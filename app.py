from flask import Flask, render_template, request, Response
from flask.helpers import make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import arrow
import git
import requests
from sqlalchemy import func
from flask import redirect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# GLOBALS

wallpapers = {
    'PLojoJXOIKgHolGTRXuYufZiMuqTZSQOgeYWpxKY': 'APOD',
    'HVyRnfHJTrZrfJHTzLcIwaulLMojMTyVPyMEEWQZ': 'PPOW',
}

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
    wallpaper = db.Column(db.String, nullable=True)
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



@app.route('/OftOfnhSdfIfHdvzrHfVwhqDiOZluDuLkNbqCiKh/<wallpaper>/<ip>', methods=['POST'])
def wallpaper_create(wallpaper, ip):
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = '*'

    try:
        latest_entry = WallpaperData.query.filter_by(ip=ip).order_by(WallpaperData.created_on.desc()).first()
        if latest_entry and datetime.utcnow() - latest_entry.created_on < timedelta(minutes=1):
            raise BaseException('Chill out.')
        db.session.add(WallpaperData(
            ip=ip,
            wallpaper=wallpapers.get(wallpaper),
        ))
        db.session.commit()
        response.data = "Success!"
        response.status_code = 200
    except BaseException as e:
        response.data = str(e)
        response.status_code = 500
        response.headers['Access-Control-Allow-Origin'] = '*'

    return response



@app.route('/wallpaper_read/')
@app.route('/wallpaper_read/<key>')
def wallpaper_read(key=''):
    if key != '':
        response = make_response(redirect('/wallpaper_read/'))
        response.set_cookie('key', 'esx')
        return response

    if request.cookies.get('key') != 'esx':
        return 'Fuck off.'

    results = db.session.query(
        WallpaperData.ip,
        WallpaperData.wallpaper,
        WallpaperData.created_on,
        func.count(WallpaperData.ip).label('count')
    ).group_by(
        WallpaperData.ip,
        WallpaperData.wallpaper
    ).order_by(WallpaperData.created_on.desc()).limit(100).all()
    data = []

    for result in results:
        data.append({
            'created_on': result.created_on,
            'ip': result.ip,
            'wallpaper': result.wallpaper,
            'count': result.count
        })

    attributes = ['country', 'region', 'city', 'isp', 'lat', 'lon']
    for result in results:
        if result.ip not in cache:
            cache[result.ip], response = {}, {}
            
            try:
                response = requests.get(f'http://ip-api.com/json/{result.ip}').json()
            except:
                print('something went wrong')

            for attribute in attributes:
                cache[result.ip][attribute] = response.get(attribute, '')
            cache[result.ip]['map'] = f'https://www.google.com/maps/search/?api=1&query={cache[result.ip]["lat"]},{cache[result.ip]["lon"]}'

    for datum in data:
        for attribute in attributes + ['map']:
            datum[attribute] = cache[datum['ip']][attribute]

    return render_template(
        'wallpaper_read.html',
        apod=list(filter(lambda x: x['wallpaper'] == 'APOD', data)),
        ppow=list(filter(lambda x: x['wallpaper'] == 'PPOW', data)),
        arrow=arrow,
    )


@app.route('/wallpaper/<wallpaper>')
def wallpaper(wallpaper):
    image = 'https://us.123rf.com/450wm/ihorsvetiukha/ihorsvetiukha1710/ihorsvetiukha171000035/87328765-matrix-falling-numbers-warning-error-404-page-not-found-vector-illustration.jpg?ver=6'
    
    if wallpaper == 'apod':
        image = requests.get('https://api.nasa.gov/planetary/apod?api_key=RkB6zuLJeCTiehSpZswRNqyoYwUYJRnO274U7wrB').json()['hdurl']
    
    return render_template(
        'wallpapers/base.html',
        image=image
    )
