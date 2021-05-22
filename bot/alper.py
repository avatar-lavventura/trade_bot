#!/usr/bin/env python3

import asyncio

import ccxt.async_support as ccxt
from quart import Quart

loop = asyncio.get_event_loop()
app = Quart(__name__)


class Exchange:
    def __init__(self):
        ops = {
            "options": {"adustForTimeDifference": True},
        }
        self.future = ccxt.binanceusdm(ops)
        self.spot = ccxt.binance(ops)


# exchange = Exchange()  # I want to create this instance only one time


@app.route("/")
async def hello():
    exchange = Exchange()
    output = await exchange.future.fetch_ticker("BTC/USDT")  # error occurs
    print(output)
    return "OK"


if __name__ == "__main__":
    app.run("", port=5000, debug=False)
