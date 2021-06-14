from datetime import datetime, timedelta
from random import choices
from string import ascii_letters, digits

import requests
from flask import current_app as app

GET_TICKER_OBJECTS_LAST = None
GET_TICKER_OBJECTS_LAST_RETURN = []


def get_ticker_objects(tickers):
    global GET_TICKER_OBJECTS_LAST
    global GET_TICKER_OBJECTS_LAST_RETURN
    if (
        GET_TICKER_OBJECTS_LAST is None
        or GET_TICKER_OBJECTS_LAST < datetime.utcnow() - timedelta(minutes=6)
    ):
        GET_TICKER_OBJECTS_LAST = datetime.utcnow()
        ticker_objects = []
        for ticker in tickers:
            try:
                current_key = next(app.config.get("STOCK_API_KEYS"))
                ticker_objects.append(
                    requests.get(
                        f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={current_key}"
                    ).json()[0]
                )
            except Exception as e:
                print(f"BACK-END: {e}")
        GET_TICKER_OBJECTS_LAST_RETURN = ticker_objects
    return GET_TICKER_OBJECTS_LAST_RETURN


def get_random_string(length=10):
    return "".join(choices(ascii_letters + digits, k=length))


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
