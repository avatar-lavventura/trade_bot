#!/usr/bin/env python3

import pickle
from pathlib import Path

import ccxt
from ebloc_broker.broker._utils.yaml import Yaml

HOME = Path.home()
_cfg = Yaml(HOME / ".binance.yaml")
api_key = str(_cfg["b"]["key"])
api_secret = str(_cfg["b"]["secret"])
ops = {"apiKey": api_key, "secret": api_secret, "options": {"adustForTimeDifference": True}}
exchange = ccxt.binance(ops)
with open(".secret.pk", "wb") as f:
    pickle.dump(exchange, f, pickle.HIGHEST_PROTOCOL)
