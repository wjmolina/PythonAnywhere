from itertools import cycle

SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
SQLALCHEMY_TRACK_MODIFICATIONS = False

HOST = "http://127.0.0.1:5000"

READ_IMAGE_INTERVAL = 5 * 1000
CREATE_LOG_INTERVAL = 1 * 1000
REFRESH_INTERVAL = 12 * 60 * 60 * 1000

SEND_EMAIL_SENDER = ""
SEND_EMAIL_RECEIVERS = ""
SEND_EMAIL_PASSWORD = ""

STOCK_API_KEYS = cycle("demo".split(","))

GOMOKU_MOVE_TIME = {"minutes": 5}
GOMOKU_MOVE_TIME_IDLE = {"seconds": 30}

JOBS = [
    {
        "id": "ai_player",
        "func": "ai_player",
        "trigger": "interval",
        "seconds": 5,
    }
]
SCHEDULER_API_ENABLED = True
