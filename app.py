import re
from datetime import datetime

import arrow
import git
import requests
from flask import Flask, Response, redirect, render_template, request
from flask.helpers import make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sqlite3.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# GLOBALS

HOST = "http://wjm.pythonanywhere.com"
# HOST = 'http://127.0.0.1:5000'

READ_IMAGE_INTERVAL = 60 * 1000
CREATE_LOG_INTERVAL = 1 * 1000
REFRESH_INTERVAL = 24 * 60 * 60 * 1000

# MODELS


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_agent = db.Column(db.String(120), nullable=False)


class AnonymousName(db.Model):
    anonymous_name = db.Column(db.String(120), primary_key=True)
    user_agent = db.Column(
        db.String(120), db.ForeignKey("comment.user_agent"), unique=True
    )


class WallpaperData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False)
    wallpaper = db.Column(db.String, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


db.create_all()

# ENDPOINTS

cache = {}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and request.form["text"]:
        db.session.add(
            Comment(text=request.form["text"], user_agent=request.headers["User-Agent"])
        )
        user_agent = (
            db.session.query(AnonymousName)
            .filter_by(user_agent=request.headers["User-Agent"])
            .first()
        )
        if not user_agent:
            anonymous_name = (
                db.session.query(AnonymousName).filter_by(user_agent=None).first()
            )
            anonymous_name.user_agent = request.headers["User-Agent"]
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


@app.route("/wallpaper/<wallpaper>/<ip>", methods=["POST"])
def wallpaper_create(wallpaper, ip):
    response = Response()

    try:
        user = WallpaperData.query.filter_by(ip=ip).first()
        user.count += 1
        db.session.commit()
        response.data = "Success!"
        response.status_code = 200
    except BaseException as e:
        response.data = str(e)
        response.status_code = 500

    return response


@app.route("/wallpaper_read/")
@app.route("/wallpaper_read/<key>")
def wallpaper_read(key=""):
    password = "esx"

    if key != "":
        response = make_response(redirect("/wallpaper_read/"))
        response.set_cookie("key", password)
        return response

    if request.cookies.get("key") != password:
        return "How in the world did you end up here?"

    results = (
        db.session.query(
            WallpaperData.ip,
            WallpaperData.wallpaper,
            WallpaperData.count,
            WallpaperData.created_on,
        )
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
            }
        )

    attributes = ["country", "region", "city", "isp", "lat", "lon"]
    for result in results:
        if result.ip not in cache:
            cache[result.ip], response = {}, {}

            try:
                response = requests.get(f"http://ip-api.com/json/{result.ip}").json()
            except:
                print("something went wrong")

            for attribute in attributes:
                cache[result.ip][attribute] = response.get(attribute, "")

    for datum in data:
        for attribute in attributes:
            datum[attribute] = cache[datum["ip"]][attribute]

    return render_template(
        "wallpapers/analytics.html",
        apod=[x for x in data if x["wallpaper"] == "apod"],
        ppow=[x for x in data if x["wallpaper"] == "ppow"],
        arrow=arrow,
    )


@app.route("/wallpaper/<wallpaper>")
def wallpaper(wallpaper):
    return render_template(
        "wallpapers/index.html",
        image_url=f"{HOST}/wallpaper/{wallpaper}/image_url",
        wallpaper=wallpaper,
        read_image_interval=READ_IMAGE_INTERVAL,
        create_log_interval=CREATE_LOG_INTERVAL,
        refresh_interval=REFRESH_INTERVAL,
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
