#!/usr/bin/env python3

import os
from pathlib import Path

import ccxt  # noqa: E402
from broker._utils.tools import log
from user_setup import check_binance_obj

HOME = str(Path.home())


def set_leverage(symbol):
    try:
        market = exchange.market(symbol)
        response = exchange.fapiPrivate_post_leverage({"symbol": market["id"], "leverage": leverage,})
        print(response)
    except Exception as e:
        log(f"E: {e}", color="red")


_file = f"{HOME}/.binance.txt"
if not os.path.exists(_file):
    with open(_file, "w"):
        pass

file1 = open(_file, "r")
Lines = file1.readlines()
api_key = str(Lines[0].strip())
api_secret = str(Lines[1].strip())

exchange = ccxt.binance(
    {
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
        "options": {"defaultType": "future",},
    }
)
exchange.load_markets()

client, _ = check_binance_obj()
futures = client.futures_position_information()
leverage = 1
for future in futures:
    symbol = future["symbol"].replace("USDT", "/USDT")
    symbol = symbol.replace("BUSD", "/BUSD")
    set_leverage(symbol)
