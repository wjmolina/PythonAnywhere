import re
from random import randint
from subprocess import PIPE, Popen
import sys
from time import sleep
from typing import Set

import requests


class Engine:
    def __init__(self, name, timeout_turn_sec):
        print(name)
        self.name = name
        self.timeout_turn_sec = int(timeout_turn_sec)
        self.reset(True)

    def reset(self, is_new=False):
        print("\nNEW GAME!")
        if not is_new:
            self.end()
        self.mind = set()
        self.p = Popen(
            ["wine", f"{self.name}.exe"], stdin=PIPE, stdout=PIPE, encoding="ascii"
        )
        self.p.stdin.write(f"INFO timeout_turn {self.timeout_turn_sec * 1000}\n")
        self.p.stdin.write("START 19\n")
        self.p.stdin.flush()
        while self.p.stdout.readline().strip() != "OK":
            pass

    def end(self):
        self.p.stdin.write("END\n")
        self.p.stdin.flush()

    def __del__(self):
        self.end()

    def begin(self) -> int:
        self.p.stdin.write("BEGIN\n")
        self.p.stdin.flush()
        while not re.match(r"^\d+,\d+$", move := self.p.stdout.readline().strip()):
            pass
        row, col = move.split(",")
        move = int(row) * 19 + int(col)
        self.mind.add(move)
        return move

    def turn(self, move: int) -> int:
        self.mind.add(move)
        row, col = move // 19, move % 19
        self.p.stdin.write(f"TURN {row},{col}\n")
        self.p.stdin.flush()
        while not re.match(r"^\d+,\d+$", new_move := self.p.stdout.readline().strip()):
            pass
        new_row, new_col = new_move.split(",")
        new_move = int(new_row) * 19 + int(new_col)
        self.mind.add(new_move)
        return new_move

    def play(self, moves: Set[int]) -> int:
        if len(moves) in {0, 1}:
            self.reset()
        if not moves:
            new_move = self.begin()
            print(f"MY: {new_move // 19:02},{new_move % 19:02}")
            return new_move
        move = list(moves - self.mind)[0]
        print(f"HE: {move // 19:02},{move % 19:02}")
        print("THINK ...")
        new_move = self.turn(move)
        print(f"MY: {new_move // 19:02},{new_move % 19:02}")
        return new_move


engine = Engine(sys.argv[1], sys.argv[2])
while True:
    try:
        # sleep(1)
        raw_moves = requests.get(
            f"http://wjm.pythonanywhere.com/wallpaper/gomoku_board/{engine.name}"
        ).text
        if "your turn" not in raw_moves:
            continue
        moves = {
            move
            for move, piece in enumerate(re.findall(r"player[exo]", raw_moves))
            if piece != "playere"
        }
        requests.post(
            f"http://wjm.pythonanywhere.com/wallpaper/gomoku/{engine.name}/{engine.play(moves)}"
        )
    except Exception as exception:
        print(f"HICCUP: {exception}")
