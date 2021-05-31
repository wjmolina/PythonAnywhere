import os
import smtplib
import ssl
from datetime import datetime, timedelta
from itertools import cycle

import requests

SEND_EMAIL_SENDER = os.getenv("SEND_EMAIL_SENDER", "")
SEND_EMAIL_RECEIVERS = os.getenv("SEND_EMAIL_RECEIVERS", "").split(" ")
SEND_EMAIL_PASSWORD = os.getenv("SEND_EMAIL_PASSWORD", "")
STOCK_API_KEY = cycle(os.getenv("STOCK_API_KEY", "").split(","))

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
        tickers = ["MSFT", "MA", "GOOG", "AMZN", "AAPL", "TSLA", "V", "SBUX", "NVDA"]
        ticker_objects = []
        for ticker in tickers:
            try:
                current_key = next(STOCK_API_KEY)
                ticker_objects.append(
                    requests.get(
                        f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={current_key}"
                    ).json()[0]
                )
            except Exception as e:
                print(f"BACK-END: {e}")
        GET_TICKER_OBJECTS_LAST_RETURN = ticker_objects
    return GET_TICKER_OBJECTS_LAST_RETURN


def send_email(hits):
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as server:
        server.login(SEND_EMAIL_SENDER, SEND_EMAIL_PASSWORD)
        for email_receiver in SEND_EMAIL_RECEIVERS:
            server.sendmail(
                SEND_EMAIL_SENDER,
                email_receiver,
                f"Subject: From the EsX Back-End\n\nThe wallpapers have been served to {hits} unique IPs.",
            )
