#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import Final

import ccxt.async_support as ccxt

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


class Exchange:
    def __init__(self):
        print("====================================================================helperrrrrrrrrrrrrrrrrrrrrrrr")
        ops = {
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"adustForTimeDifference": True},
            # 'verbose': True,  # for debug output
        }
        self.future: Final = ccxt.binanceusdm(ops)
        self.spot: Final = ccxt.binance(ops)


exchange = Exchange()
