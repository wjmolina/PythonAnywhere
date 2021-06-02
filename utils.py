from datetime import datetime, timedelta
from random import choices
from string import ascii_letters, digits

import requests
from flask import current_app as app

GET_TICKER_OBJECTS_LAST = None
GET_TICKER_OBJECTS_LAST_RETURN = []


def get_ticker_objects():
    global GET_TICKER_OBJECTS_LAST
    global GET_TICKER_OBJECTS_LAST_RETURN
    if (
        GET_TICKER_OBJECTS_LAST is None
        or GET_TICKER_OBJECTS_LAST < datetime.utcnow() - timedelta(minutes=6)
    ):
        GET_TICKER_OBJECTS_LAST = datetime.utcnow()
        tickers = ["MSFT", "MA", "GOOG", "AMZN", "AAPL", "TSLA", "V", "AMC", "NVDA"]
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
