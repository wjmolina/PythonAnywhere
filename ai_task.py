from random import choice
from time import sleep

import requests
from sqlalchemy import and_, or_

from app import app
from models import Game, Player

while True:
    requests.get(app.config["HOST"] + "/wallpaper/gomoku_board/ai_task")

    player = Player.query.filter_by(ip="ai_task").first()

    game: Game = Game.query.filter(
        and_(or_(Game.white == player.id, Game.black == player.id), Game.winner == "0")
    ).first()

    if (
        game.get_turn() == "1"
        and game.white == player.id
        or game.get_turn() == "2"
        and game.black == player.id
    ):
        response = requests.get(
            f"https://apps.yunzhu.li/gomoku/move?s={game.state}"
        ).json()
        try:
            game.put_move(
                int(response["result"]["move_r"]) * 19
                + int(response["result"]["move_c"])
            )
        except:
            game.put_move(choice([i for i, x in enumerate(game.state) if x == "0"]))

    sleep(1)
