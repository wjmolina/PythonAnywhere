import re
import smtplib
import ssl
from datetime import datetime, timedelta

import arrow
import flask
import git
import requests
from flask import Flask, Response, render_template, request
from flask_sqlalchemy import SQLAlchemy

from utils import get_random_string, get_ticker_objects

app = Flask(__name__)

app.config.from_object("default_config")
try:
    app.config.from_object("config")
except:
    print("INFO: could not load config.py")

db = SQLAlchemy(app)

from models import AnonymousName, Comment, IpNotes, UhComments, WallpaperData


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and request.form["text"]:
        print(request)
        db.session.add(
            Comment(text=request.form["text"], user_agent=request.headers["User-Agent"])
        )
        user_agent = (
            db.session.query(AnonymousName)
            .filter_by(user_agent=request.headers["User-Agent"])
            .first()
        )
        if not user_agent:
            db.session.add(
                AnonymousName(
                    user_agent=request.headers["User-Agent"],
                    anonymous_name=get_random_string(),
                )
            )
        db.session.commit()
    return render_template("index.html", comments=comments())


@app.route("/comments")
def comments():
    comments = (
        Comment.query.join(
            AnonymousName, Comment.user_agent == AnonymousName.user_agent
        )
        .add_columns(AnonymousName.anonymous_name, Comment.created_on, Comment.text)
        .all()
    )
    return render_template("comments.html", comments=comments[::-1], arrow=arrow)


@app.route("/update_server", methods=["POST"])
def webhook():
    repo = git.Repo("application")
    origin = repo.remotes.origin
    origin.pull()
    return "updated PythonAnywhere successfully"


@app.route("/wallpaper/notes/<ip>", methods=["GET", "POST"])
def wallpaper_read_notes(ip):
    if flask.request.method == "POST":
        try:
            note = request.form["note"].strip()
            if note:
                db.session.add(IpNotes(ip=ip, note=note))
                db.session.commit()
        except BaseException as e:
            return str(e), 500
    return render_template(
        "wallpapers/notes.html",
        arrow=arrow,
        ip=ip,
        notes=IpNotes.query.filter_by(ip=ip).order_by(IpNotes.created_on.desc()).all(),
    )


@app.route("/wallpaper/<wallpaper>/<ip>", methods=["POST"])
def wallpaper_create(wallpaper, ip):
    response = Response()

    try:
        user = WallpaperData.query.filter(
            (WallpaperData.ip == ip) & (WallpaperData.wallpaper == wallpaper)
        ).first()
        if not user:
            user = WallpaperData(
                ip=ip,
                wallpaper=wallpaper,
                count=1,
            )
            db.session.add(user)
        else:
            user.count += 1
        user.created_on = datetime.utcnow()
        db.session.commit()
        response.data = "Success!"
        response.status_code = 200
    except BaseException as e:
        print(f"BACK-END: COULD NOT LOG IP, {e}")
        response.data = str(e)
        response.status_code = 500

    try:
        with open("/home/wjm/application/.milestones", "r+") as file:
            total_hits = (
                db.session.query(WallpaperData)
                .distinct(WallpaperData.ip)
                .group_by(WallpaperData.ip)
                .count()
            )
            data = file.read()
            if not total_hits % 100 and total_hits > int(data):
                try:
                    send_email(
                        f"Subject: From the EsX Back-End\n\nThe wallpapers have been served to {total_hits} unique IPs."
                    )
                except BaseException as e:
                    print(f"BACK-END: COULD NOT SEND EMAIL, {e}")
            file.seek(0)
            file.write(str(total_hits))
            file.truncate()
    except BaseException as e:
        print(f"BACK-END: COULD NOT SEND EMAIL, {e}")
        response.data = str(e)
        response.status_code = 500

    return response


wallpaper_read_cache = {}


@app.route("/wallpaper_read/")
def wallpaper_read():
    results = (
        db.session.query(
            WallpaperData.ip,
            WallpaperData.wallpaper,
            WallpaperData.count,
            WallpaperData.created_on,
        )
        .filter(WallpaperData.created_on > datetime.utcnow() - timedelta(days=4))
        .order_by(WallpaperData.created_on.desc())
        .all()
    )
    data = []

    for result in results:
        data.append(
            {
                "created_on": result.created_on,
                "ip": result.ip,
                "wallpaper": result.wallpaper,
                "count": result.count,
                "notes_count": IpNotes.query.filter_by(ip=result.ip).count(),
            }
        )

    attributes = ["country", "region", "city", "isp", "lat", "lon"]
    for result in results:
        if result.ip not in wallpaper_read_cache:
            response = {}
            try:
                clean_ip = result.ip[1 if result.ip[0] == "E" else 0 :]
                response = requests.get(f"http://ip-api.com/json/{clean_ip}").json()
            except BaseException as e:
                print(f"BACK-END: COULD NOT GET IP INFO, {e}")
                continue

            wallpaper_read_cache[result.ip] = {}
            for attribute in attributes:
                wallpaper_read_cache[result.ip][attribute] = response.get(attribute, "")

    for datum in data:
        for attribute in attributes:
            datum[attribute] = wallpaper_read_cache.get(datum["ip"], {}).get(
                attribute, ""
            )

    apod = {
        "wallpaper": [x for x in data if x["wallpaper"] == "apod"],
        "name": "Astronomy Picture of the Day",
        "url": "apod",
    }
    ppow = {
        "wallpaper": [x for x in data if x["wallpaper"] == "ppow"],
        "name": "Perseverance Picture of the Week",
        "url": "ppow",
    }

    return render_template(
        "wallpapers/analytics.html",
        host=app.config["HOST"],
        items=[apod, ppow],
        arrow=arrow,
    )


@app.route("/wallpaper/<wallpaper>")
def wallpaper(wallpaper):
    if wallpaper == "tickertracker":
        return render_template(
            "wallpapers/tickerTracker.html", ticker_objects=get_ticker_objects()
        )
    return render_template(
        "wallpapers/index.html",
        image_url=f"{app.config['HOST']}/wallpaper/{wallpaper}/image_url",
        wallpaper=wallpaper,
        read_image_interval=app.config["READ_IMAGE_INTERVAL"],
        create_log_interval=app.config["CREATE_LOG_INTERVAL"],
        refresh_interval=app.config["REFRESH_INTERVAL"],
    )


@app.route("/wallpaper/<wallpaper>/image_url")
def wallpaper_image_url(wallpaper):
    if wallpaper == "apod":
        return {
            "image_url": requests.get(
                "https://api.nasa.gov/planetary/apod?api_key=RkB6zuLJeCTiehSpZswRNqyoYwUYJRnO274U7wrB"
            ).json()["hdurl"]
        }
    if wallpaper == "ppow":
        return {
            "image_url": re.findall(
                r'og:image" content="(.*?)"',
                requests.get(
                    "https://mars.nasa.gov/mars2020/multimedia/raw-images/image-of-the-week/"
                ).text,
            )[0]
        }


@app.route("/wjmolina", methods=["GET", "POST"])
def wjmolina():
    if request.method == "POST":
        text = request.form["text"].strip()
        if text:
            db.session.add(UhComments(text=text))
            db.session.commit()
    return render_template(
        "uhpage.html",
        comments=UhComments.query.order_by(UhComments.created_on.desc()).all(),
    )


@app.route("/send_email", methods=["POST"])
def send_email(message=None):
    print("asdkjashdjkasdhaksd", app.config.get("SEND_EMAIL_SENDER"))
    print("asdkjashdjkasdhaksd", app.config.get("SEND_EMAIL_PASSWORD"))
    print("asdkjashdjkasdhaksd", app.config.get("SEND_EMAIL_RECEIVERS"))
    print("asdkjashdjkasdhaksd", app.config.get("SEND_EMAIL_SENDER"))
    # if message is None:
    #     message = request.json["message"]
    # with smtplib.SMTP_SSL(
    #     "smtp.gmail.com", 465, context=ssl.create_default_context()
    # ) as server:
    #     server.login(
    #         app.config.get("SEND_EMAIL_SENDER"), app.config.get("SEND_EMAIL_PASSWORD")
    #     )
    #     for email_receiver in app.config.get("SEND_EMAIL_RECEIVERS"):
    #         server.sendmail(
    #             app.config.get("SEND_EMAIL_SENDER"),
    #             email_receiver,
    #             message,
    #         )
