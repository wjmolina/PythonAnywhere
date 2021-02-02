from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import arrow
import git

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
db.create_all()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_agent = db.Column(db.String(120), nullable=False)


class AnonymousName(db.Model):
    anonymous_name = db.Column(db.String(120), primary_key=True)
    user_agent = db.Column(db.String(120), db.ForeignKey('comment.user_agent'), unique=True)


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
