#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path

import ccxt

HOME = str(Path.home())
_file = f"{HOME}/.binance.txt"
if not os.path.exists(_file):
    with open(_file, "w"):
        pass

try:
    file_to_open = open(_file, "r")
    Lines = file_to_open.readlines()
    api_key = str(Lines[0].strip())
    api_secret = str(Lines[1].strip())
except:
    sys.exit(1)

ops = {"apiKey": api_key, "secret": api_secret, "options": {"adustForTimeDifference": True}}
exchange = ccxt.binance(ops)

_file = ".secret.pk"
with open(_file, "wb") as f:
    pickle.dump(exchange, f, pickle.HIGHEST_PROTOCOL)
