from flask import Flask, render_template, request, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import arrow
import git
import requests
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# MODELS

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_agent = db.Column(db.String(120), nullable=False)


class AnonymousName(db.Model):
    anonymous_name = db.Column(db.String(120), primary_key=True)
    user_agent = db.Column(db.String(120), db.ForeignKey('comment.user_agent'), unique=True)


class WallpaperData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


db.create_all()

# ENDPOINTS

cache = {}

@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST' and request.form['text']:
        db.session.add(Comment(
            text=request.form['text'],
            user_agent=request.headers['User-Agent']
        ))
        user_agent = db.session.query(AnonymousName).filter_by(user_agent=request.headers['User-Agent']).first()
        if not user_agent:
            anonymous_name = db.session.query(AnonymousName).filter_by(user_agent=None).first()
            anonymous_name.user_agent = request.headers['User-Agent']
        db.session.commit()
    return render_template('index.html', comments=comments())


@app.route('/comments')
def comments():
    comments = Comment.query.join(
        AnonymousName,
        Comment.user_agent == AnonymousName.user_agent
    ).add_columns(
        AnonymousName.anonymous_name,
        Comment.created_on,
        Comment.text
    ).all()
    return render_template('comments.html', comments=comments[::-1], arrow=arrow)


@app.route('/update_server', methods=['POST'])
def webhook():
    repo = git.Repo('application')
    origin = repo.remotes.origin
    origin.pull()
    return 'updated PythonAnywhere successfully'



@app.route('/wallpaper_create/<ip>', methods=['POST'])
def wallpaper_create(ip):
    try:
        db.session.add(WallpaperData(
            ip=ip
        ))
        db.session.commit()
        resp = Response("success")
        resp.status_code = 200
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except:
        resp = Response("failure")
        resp.status_code = 500
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp



@app.route('/wallpaper_read')
def wallpaper_read():
    results = db.session.query(WallpaperData.ip, WallpaperData.created_on, func.count(WallpaperData.ip).label('count')).group_by(WallpaperData.ip).order_by(WallpaperData.created_on.desc()).limit(100).all()
    data = []

    for result in results:
        data.append({'created_on' : result.created_on.strftime('%A, %B %d, %Y @ %I:%M:%S %p'), 'ip': result.ip, 'count': result.count})

    attributes = ['country', 'region', 'city', 'isp', 'lat', 'lon']
    for result in results:
        if result.ip not in cache:
            cache[result.ip], response = {}, {}
            
            try:
                response = requests.get(f'http://ip-api.com/json/{result.ip}').json()
            except:
                print('something went wrong')

            for attribute in attributes:
                cache[result.ip][attribute] = response.get(attribute, 'TBD')
            cache[result.ip]['map'] = f'https://www.google.com/maps/search/?api=1&query={cache[result.ip]["lat"]},{cache[result.ip]["lon"]}'

        for attribute in attributes + ['map']:
            for datum in data:
                datum[attribute] = cache[result.ip][attribute]

    return render_template(
        'wallpaper_read.html',
        data=data
    )
