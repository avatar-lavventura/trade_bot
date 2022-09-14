#!/usr/bin/env python3

import pickle
from pathlib import Path

import ccxt
from broker._utils.yaml import Yaml

HOME = Path.home()
_cfg = Yaml(HOME / ".binance.yaml")
k = "alper_b"
api_key = str(_cfg[k]["key"])
api_secret = str(_cfg[k]["secret"])
ops = {"apiKey": api_key, "secret": api_secret, "options": {"adustForTimeDifference": True}}
exchange = ccxt.binance(ops)
with open(".secret.pk", "wb") as f:
    pickle.dump(exchange, f, pickle.HIGHEST_PROTOCOL)
