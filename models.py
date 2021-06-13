from datetime import datetime
from random import choice

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
    state = db.Column(db.String, nullable=False, default="0" * 19 * 19)
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
        for i in range(15):
            for j in range(19):
                if self.state[i * 19 + j] != "0" and all(
                    self.state[i * 19 + j] == self.state[(i + k) * 19 + j]
                    for k in range(5)
                ):
                    return self.state[i * 19 + j]
        for i in range(19):
            for j in range(15):
                if self.state[i * 19 + j] != "0" and all(
                    self.state[i * 19 + j] == self.state[i * 19 + j + k]
                    for k in range(5)
                ):
                    return self.state[i * 19 + j]
        for i in range(15):
            for j in range(15):
                if self.state[i * 19 + j] != "0" and all(
                    self.state[i * 19 + j] == self.state[(i + k) * 19 + j + k]
                    for k in range(5)
                ):
                    return self.state[i * 19 + j]
        for i in range(15):
            for j in range(4, 19):
                if self.state[i * 19 + j] != "0" and all(
                    self.state[i * 19 + j] == self.state[(i + k) * 19 + j - k]
                    for k in range(5)
                ):
                    return self.state[i * 19 + j]
        return "0" if self.state.count("0") else "d"

    def put_random_move(self):
        def next_to_opp_moves():
            result = []
            for pos, pce in enumerate(self.state):
                if pce == "0":
                    i, j = pos // 19, pos % 19
                    for k in range(-1, 2):
                        for l in range(-1, 2):
                            if (
                                {k, l} != {0}
                                and 0 <= (i + k) * 19 + (j + l) < 361
                                and self.state[(i + k) * 19 + (j + l)] != "0"
                            ):
                                result.append(pos)
            return result or [choice(range(361))]

        ai_move = None

        # ai_move = alpha_beta(
        #     self, 4, float("-inf"), float("inf"), self.get_turn() == "1"
        # )[1]

        if not ai_move:
            ai_move = choice(next_to_opp_moves())

        self.put_move(ai_move)

    def is_terminal(self):
        return self.get_winner() in {"1", "2", "d"}

    def children(self):
        for move, pos in enumerate(self.state):
            if pos == "0":
                child = Game(state=str(self.state))
                child.put_move(move)
                yield child, move

    def value(self):
        return (
            float("inf")
            if (winner := self.get_winner()) == "1"
            else float("-inf")
            if winner == "2"
            else 0
        )


def alpha_beta(node, depth, alpha, beta, is_max_p):
    if not depth or node.is_terminal():
        return node.value(), None
    if is_max_p:
        value, best_move = float("-inf"), None
        for child, move in node.children():
            value, best_move = max(
                [
                    (value, best_move),
                    (alpha_beta(child, depth - 1, alpha, beta, False)[0], move),
                ],
                key=lambda x: x[0],
            )
            if value >= beta:
                break
            alpha = max(alpha, value)
        return value, best_move
    else:
        value, best_move = float("inf"), None
        for child, move in node.children():
            value, best_move = min(
                [
                    (value, best_move),
                    (alpha_beta(child, depth - 1, alpha, beta, True)[0], move),
                ],
                key=lambda x: x[0],
            )
            if value <= alpha:
                break
            beta = min(beta, value)
        return value, best_move


db.create_all()
