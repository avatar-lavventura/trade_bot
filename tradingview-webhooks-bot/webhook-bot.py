#!/usr/bin/env python3

"""
Tradingview-webhooks-bot is a python bot that works with tradingview's webhook alerts!
This bot is not affiliated with tradingview and was created by @robswc

You can follow development on github at: github.com/robswc/tradingview-webhook-bot

I'll include as much documentation here and on the repo's wiki!  I
expect to update this as much as possible to add features as they become available!
Until then, if you run into any bugs let me know!
"""

from actions import parse_webhook, send_order
from auth import get_token
from flask import Flask, abort, request

# Create Flask object called app.
app = Flask(__name__)


# Create root to easily let us know its on/working.
@app.route("/")
def root():
    return "online"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        # Parse the string data from tradingview into a python dict
        data_msg = parse_webhook(request.get_data(as_text=True))
        print(data_msg)
        print("===========================================================================")
        if data_msg:
            print(" [Alert Received] ")
            return "", 200
        else:
            abort(403)
    else:
        abort(400)


if __name__ == "__main__":
    app.run()
    # app.run(host="34.89.13.197", port="5000")
