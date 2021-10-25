#!/usr/bin/env python3

from pathlib import Path

import ccxt
from ebloc_broker.broker._utils.yaml import Yaml

HOME = Path.home()
_cfg = Yaml(HOME / ".binance.yaml")
api_key = str(_cfg["b"]["key"])
api_secret = str(_cfg["b"]["secret"])


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
