from datetime import datetime

from sqlalchemy import ForeignKey

from app import db


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


class IpNotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False)
    note = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class UhComments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False, unique=True)
    country = db.Column(db.String, nullable=True)
    region = db.Column(db.String, nullable=True)
    city = db.Column(db.String, nullable=True)
    isp = db.Column(db.String, nullable=True)
    elo = db.Column(db.Float, nullable=False, default=1000)
    updated_on = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    white = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    black = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    state = db.Column(db.String, nullable=False, default="0" * 15 * 15)
    winner = db.Column(db.String, nullable=False, default="0")
    updated_on = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def put_move(self, move):
        if self.get_winner() == "0" and self.state[int(move)] == "0":
            state = list(self.state)
            state[int(move)] = self.get_turn()
            self.state = "".join(state)
            self.winner = self.get_winner()
            db.session.commit()
            return True
        return False

    def get_turn(self):
        return "2" if (self.state.count("1") + self.state.count("2")) % 2 else "1"

    def get_winner(self):
        for i in range(11):
            for j in range(15):
                if self.state[i * 15 + j] != "0" and all(
                    self.state[i * 15 + j] == self.state[(i + k) * 15 + j]
                    for k in range(5)
                ):
                    return self.state[i * 15 + j]
        for i in range(15):
            for j in range(11):
                if self.state[i * 15 + j] != "0" and all(
                    self.state[i * 15 + j] == self.state[i * 15 + j + k]
                    for k in range(5)
                ):
                    return self.state[i * 15 + j]
        for i in range(11):
            for j in range(11):
                if self.state[i * 15 + j] != "0" and all(
                    self.state[i * 15 + j] == self.state[(i + k) * 15 + j + k]
                    for k in range(5)
                ):
                    return self.state[i * 15 + j]
        for i in range(11):
            for j in range(4, 15):
                if self.state[i * 15 + j] != "0" and all(
                    self.state[i * 15 + j] == self.state[(i - k) * 15 + j + k]
                    for k in range(5)
                ):
                    return self.state[i * 15 + j]
        return "0" if self.state.count("0") else "d"


db.create_all()
