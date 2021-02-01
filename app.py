from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import arrow
import git

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/wjm/application/sqlite3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    user_agent = db.Column(db.String(120))


@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST' and request.form['text']:
        db.session.add(Comment(
            text=request.form['text'],
            user_agent=request.headers['User-Agent']
        ))
        db.session.commit()
    comments = Comment.query.all()
    for comment in comments:
        comment.created_on = arrow.get(comment.created_on).humanize()
    return render_template('index.html', comments=comments[::-1])


@app.route('/update_server', methods=['POST'])
def webhook():
    repo = git.Repo('/home/wjm/application')
    origin = repo.remotes.origin
    origin.pull()
    return 'updated PythonAnywhere successfully', 200