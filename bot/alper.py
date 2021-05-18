#!/usr/bin/env python3

import asyncio
import time

import ccxt.async_support as ccxt
import quart.flask_patch  # noqa
from actions import parse_webhook
from broker._utils.tools import _colorize_traceback, _time, log
from flask import Flask, abort, request
from quart import Quart

import bot.trade as bot_trade

loop = asyncio.get_event_loop()
worker_loop = asyncio.new_event_loop()
# app = Quart(__name__)
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == "POST":
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            try:
                await bot_trade.bot.trade_main(data_msg)
                # loop.run_until_complete(bot_trade.bot.trade_main(data_msg))
                return "OK"
            except Exception as e:
                _colorize_traceback(e)
                log("EXCEPTION catched", color="red")
                time.sleep(15)

            return "", 200
        else:
            log("E: abort")
            abort(403)
    else:
        log("E: abort")
        abort(400)


@app.route("/")
def notify():
    return "OK"


if __name__ == "__main__":
    app.run("", port=5000, debug=True, threaded=True)
