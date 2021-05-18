#!/usr/bin/env python3

import os
from pathlib import Path

import ccxt

HOME = str(Path.home())

_file = f"{HOME}/.binance.txt"
if not os.path.exists(_file):
    with open(_file, "w"):
        pass

file1 = open(_file, "r")
Lines = file1.readlines()
api_key = str(Lines[0].strip())
api_secret = str(Lines[1].strip())


def forces_order(exchange, symbol, since=None, limit=None, params={}):
    exchange.load_markets()
    market = exchange.market(symbol)
    request = {
        "symbol": market["id"],
    }
    if since is not None:
        request["startTime"] = since
        request["endTime"] = exchange.sum(since, 3600000)
    if limit is not None:
        request["limit"] = limit  # default == max == 500
    return exchange.fapiPrivate_get_forceorders(request)


ops = {"apiKey": api_key, "secret": api_secret, "options": {"adustForTimeDifference": True}}
exchange = ccxt.binance(ops)
output = forces_order(exchange, "BTC/USDT")
print(output)
