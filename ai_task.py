import re
from time import sleep

import requests

piece_interface = {
    "playere": "0",
    "playerx": "1",
    "playero": "2",
}
is_spam = False

while True:
    text = ""

    try:
        text = requests.get(
            "http://wjm.pythonanywhere.com/wallpaper/gomoku_board/ai_task"
        ).text
    except:
        print("I couldn't get the game.")
        continue

    if "your turn" not in text:
        if not is_spam:
            print("It's not my turn.")
            is_spam = True
        continue

    is_spam = False

    try:
        state = "".join(
            piece_interface[piece] for piece in re.findall(r"static/(\S+)\.png", text)
        )
    except:
        print("I couldn't understand the response.")
        continue

    try:
        engine = requests.get("https://apps.yunzhu.li/gomoku/move?s=" + state).json()[
            "result"
        ]
    except:
        print("I couldn't get the move.")
        continue

    try:
        requests.post(
            f"http://wjm.pythonanywhere.com/wallpaper/gomoku/ai_task/{int(engine['move_r']) * 19 + int(engine['move_c'])}"
        )
    except:
        print("I couldn't make the move.")
        continue

    print("I made the move.")

    sleep(5)
