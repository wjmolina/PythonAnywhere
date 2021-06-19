import re
import smtplib
import ssl
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from random import choice, randint
from time import sleep

import arrow
import flask
import git
import requests
from flask import Flask, Response, redirect, render_template, request
from sqlalchemy import and_, or_

from models import AnonymousName, Comment, Game, IpNotes, Player, WallpaperData, db
from utils import get_random_string, get_ticker_objects

app = Flask(__name__)

app.config.from_object("default_config")
try:
    app.config.from_object("config")
except:
    print("INFO: could not load config.py")

db.init_app(app)

with app.app_context():
    db.create_all()


def ai_player():
    def next_to_opp_moves(state):
        result = []
        for pos, pce in enumerate(state):
            if pce == "0":
                i, j = pos // 19, pos % 19
                for k in range(-1, 2):
                    for l in range(-1, 2):
                        if (
                            {k, l} != {0}
                            and 0 <= (i + k) * 19 + (j + l) < 361
                            and state[(i + k) * 19 + (j + l)] != "0"
                        ):
                            result.append(pos)
        return choice(result or range(361))

    while True:
        sleep(5)
        requests.get(f"{app.config['HOST']}/wallpaper/gomoku_board/ai_player")
        ai: Player = Player.query.filter_by(ip="ai_player").first()
        game: Game = Game.query.filter(
            and_(
                or_(Game.white == ai.id, Game.black == ai.id),
                Game.winner == "0",
            )
        ).first()
        if game:
            requests.post(
                f"{app.config['HOST']}/wallpaper/gomoku/ai_player/{next_to_opp_moves(game.state)}"
            )


# scheduler = BackgroundScheduler()
# scheduler.add_job(ai_player, "interval", seconds=10)
# scheduler.start()


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

    # try:
    #     with open("/home/wjm/application/.milestones", "r+") as file:
    #         total_hits = (
    #             db.session.query(WallpaperData)
    #             .distinct(WallpaperData.ip)
    #             .group_by(WallpaperData.ip)
    #             .count()
    #         )
    #         data = file.read()
    #         if not total_hits % 100 and total_hits > int(data):
    #             try:
    #                 send_email(
    #                     f"Subject: From the EsX Back-End\n\nThe wallpapers have been served to {total_hits} unique IPs."
    #                 )
    #             except BaseException as e:
    #                 print(f"BACK-END: COULD NOT SEND EMAIL, {e}")
    #         file.seek(0)
    #         file.write(str(total_hits))
    #         file.truncate()
    # except BaseException as e:
    #     print(f"BACK-END: COULD NOT SEND EMAIL, {e}")
    #     response.data = str(e)
    #     response.status_code = 500

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
    tickertracker = {
        "wallpaper": [x for x in data if x["wallpaper"] == "tickertracker"],
        "name": "Ticker Tracker",
        "url": "tickertracker",
    }
    gomoku = {
        "wallpaper": [x for x in data if x["wallpaper"] == "gomoku"],
        "name": "Gomoku",
        "url": "gomoku",
    }

    return render_template(
        "wallpapers/analytics.html",
        items=[gomoku, tickertracker, apod, ppow],
        arrow=arrow,
    )


@app.route("/wallpaper/<wallpaper>")
def wallpaper(wallpaper):
    if wallpaper == "tickertracker":
        try:
            with open("/home/wjm/application/.tickers", "r") as tickers_file:
                tickers = tickers_file.read().split(",")
        except:
            tickers = [
                "AAPL",
                "MSFT",
                "GOOG",
                "AMZN",
                "FB",
                "BRK.A",
                "BABA",
                "TSLA",
                "TSM",
            ]
        return render_template(
            "wallpapers/tickerTracker.html",
            ticker_objects=get_ticker_objects(tickers),
            wallpaper=wallpaper,
            create_log_interval=app.config["CREATE_LOG_INTERVAL"],
            refresh_interval=5 * 1000,
            host=app.config["HOST"],
        )
    return render_template(
        "wallpapers/index.html",
        image_url=f"{app.config['HOST']}/wallpaper/{wallpaper}/image_url",
        wallpaper=wallpaper,
        read_image_interval=app.config["READ_IMAGE_INTERVAL"],
        create_log_interval=app.config["CREATE_LOG_INTERVAL"],
        refresh_interval=app.config["REFRESH_INTERVAL"],
        host=app.config["HOST"],
    )


@app.route("/wallpaper/tickertracker/update/<tickers>", methods=["POST"])
def update_tickers(tickers):
    with open("/home/wjm/application/.tickers", "w") as tickers_file:
        tickers_file.write(tickers)
    return "Success", 200


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
    return redirect("http://esx.pythonanywhere.com/")
    # if request.method == "POST":
    #     text = request.form["text"].strip()
    #     if text:
    #         db.session.add(UhComments(text=text))
    #         db.session.commit()
    # return render_template(
    #     "uhpage.html",
    #     comments=UhComments.query.order_by(UhComments.created_on.desc()).all(),
    # )


@app.route("/send_email", methods=["POST"])
def send_email(message=None):
    if message is None:
        message = request.json["message"]
    msg = MIMEText(message)
    msg["Subject"] = f"Subject: Message from {request.json['ip']}"
    msg["From"] = f"EsX Back-End <{app.config.get('SEND_EMAIL_SENDER')}>"
    msg["To"] = app.config.get("SEND_EMAIL_RECEIVERS")
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as server:
        server.login(
            app.config.get("SEND_EMAIL_SENDER"), app.config.get("SEND_EMAIL_PASSWORD")
        )
        for email_receiver in app.config.get("SEND_EMAIL_RECEIVERS").split(","):
            server.sendmail(
                app.config.get("SEND_EMAIL_SENDER"), email_receiver, msg.as_string()
            )


@app.route("/wallpaper/gomoku/", methods=["GET"])
@app.route("/wallpaper/gomoku/<ip>/<move>", methods=["POST"])
def gomoku(ip=None, move=None):
    if request.method == "GET":
        return render_template(
            "wallpapers/gomoku.html", host=app.config["HOST"], wallpaper="gomoku"
        )

    if request.method == "POST":
        player: Player = Player.query.filter_by(ip=ip).first()

        if not player:
            return "player does not exist", 500

        game: Game = Game.query.filter(
            and_(
                or_(Game.white == player.id, Game.black == player.id),
                Game.winner == "0",
            )
        ).first()

        if not game:
            return "game does not exist", 500

        if move == "giveup" or game.get_turn() == (
            "1" if game.white == player.id else "2"
        ):
            if move != "giveup":
                game.put_move(move)
                game.last_move = int(move)

            # Make this prettier later.
            if (
                winner := game.get_winner()
                if move != "giveup"
                else ("2" if game.white == player.id else "1")
            ) == "d":
                a: Player = Player.query.filter_by(id=game.white).first()
                b: Player = Player.query.filter_by(id=game.black).first()
                if a and b:
                    a.elo = a.elo + 32 * (0.5 - 1 / (10 ** ((b.elo - a.elo) / 400) + 1))
                    b.elo = b.elo + 32 * (0.5 - 1 / (10 ** ((a.elo - b.elo) / 400) + 1))
            elif winner == "1":
                w: Player = Player.query.filter_by(id=game.white).first()
                l: Player = Player.query.filter_by(id=game.black).first()
                if w and l:
                    w.elo = w.elo + 32 * (1 - 1 / (10 ** ((l.elo - w.elo) / 400) + 1))
                    l.elo = l.elo + 32 * (0 - 1 / (10 ** ((w.elo - l.elo) / 400) + 1))
            elif winner == "2":
                w: Player = Player.query.filter_by(id=game.black).first()
                l: Player = Player.query.filter_by(id=game.white).first()
                if w and l:
                    w.elo = w.elo + 32 * (1 - 1 / (10 ** ((l.elo - w.elo) / 400) + 1))
                    l.elo = l.elo + 32 * (0 - 1 / (10 ** ((w.elo - l.elo) / 400) + 1))

            if move == "giveup":
                player.elo -= player.elo * 0.01
                game.winner = winner

            db.session.commit()

            return "success", 200
        else:
            return "not your turn", 400


@app.route("/wallpaper/gomoku_board/<ip>", methods=["GET"])
def gomoku_board(ip):
    def get_move_timedelta(game: Game):
        if all([game.white, game.black]):
            if game.state.count("1") + game.state.count("2") < 3:
                return timedelta(**app.config.get("GOMOKU_MOVE_TIME_IDLE"))
            return timedelta(**app.config.get("GOMOKU_MOVE_TIME"))
        return timedelta(days=1)

    def get_seconds_left(game):
        if all([game.white, game.black]):
            return (
                get_move_timedelta(game) + game.updated_on - datetime.utcnow()
            ).total_seconds()
        return "∞"

    # Get or create the player associated to the given IP.
    player: Player = Player.query.filter_by(ip=ip).first()
    if not player:
        response = requests.get(f"http://ip-api.com/json/{ip}").json()
        player = Player(
            ip=ip,
            country=response.get("country"),
            region=response.get("region"),
            city=response.get("city"),
            isp=response.get("isp"),
        )
        db.session.add(player)
        db.session.commit()
        player: Player = Player.query.filter_by(ip=ip).first()

    # Get or create the game associated to the player.
    game: Game = Game.query.filter(
        and_(
            or_(Game.white == player.id, Game.black == player.id),
            Game.winner == "0",
        )
    ).first()
    if not game:
        game: Game = Game.query.filter(
            and_(
                or_(
                    and_(Game.white == None, Game.black != player.id),
                    and_(Game.black == None, Game.white != player.id),
                ),
                Game.winner == "0",
            )
        ).first()
        if game:
            if game.white is None:
                game.white = player.id
            else:
                game.black = player.id
        else:
            if randint(1, 2) == 1:
                game = Game(white=player.id)
            else:
                game = Game(black=player.id)
            db.session.add(game)
        db.session.commit()
        game: Game = Game.query.filter(
            and_(
                or_(Game.white == player.id, Game.black == player.id),
                Game.winner == "0",
            )
        ).first()

    # Check whether the game is finished.
    seconds_left = get_seconds_left(game)
    if seconds_left != "∞" and seconds_left <= 0:
        if game.state.count("1") + game.state.count("2") < 3:
            db.session.delete(game)
        else:
            game.winner = "1" if game.get_turn() == "2" else "2"
        db.session.commit()

    # Get the opponent.
    if game.white == player.id:
        opponent: Player = Player.query.filter_by(id=game.black).first()
    else:
        opponent = Player.query.filter_by(id=game.white).first()

    # Get the player's score.
    finished_games = Game.query.filter(Game.winner != "0")
    scores = defaultdict(lambda: [0, 0, 0])
    for plyr in Player.query.all():
        for finished_game in finished_games:
            if (
                finished_game.white == plyr.id
                and finished_game.winner == "1"
                or finished_game.black == plyr.id
                and finished_game.winner == "2"
            ):
                scores[plyr.id][0] += 1
            elif finished_game.winner == "d":
                scores[plyr.id][1] += 1
            else:
                scores[plyr.id][2] += 1

    players = [
        {
            "name": player.name,
            "elo": player.elo,
            "w": scores[player.id][0],
            "l": scores[player.id][2],
            "d": scores[player.id][1],
        }
        for player in Player.query.filter(
            Player.updated_on > datetime.utcnow() - timedelta(days=1)
        ).order_by(Player.elo.desc())
    ]

    return render_template(
        "wallpapers/gomokuBoard.html",
        state=game.state,
        turn=(
            "your turn"
            if game.get_turn() == ("1" if game.white == player.id else "2")
            else "opponent's turn"
            if all([game.white, game.black])
            else "waiting for opponent"
        ),
        win=scores[player.id][0],
        loss=scores[player.id][2],
        draw=scores[player.id][1],
        seconds=get_seconds_left(game),
        total_seconds=get_move_timedelta(game).total_seconds(),
        your_elo=f"{player.elo:0.0f}",
        opponent_elo=f"{opponent.elo:0.0f}" if opponent else "???",
        your_name=(player.name or "").strip() or None,
        opponent_name=((opponent.name if opponent else "???") or "").strip() or None,
        last_move=game.last_move,
        players=players,
    )


@app.route("/wallpaper/gomoku/change_name/<ip>/<name>", methods=["POST"])
def change_name(ip, name):
    player = Player.query.filter_by(ip=ip).first()
    player.name = name
    db.session.commit()
    return "success"
