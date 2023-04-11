#!/usr/bin/env python3

import time

from broker._utils._log import log


def fetch_withdrawn(sh, asset) -> float:
    column = ""
    if asset == "usdt":
        column = "L2"
    elif asset == "btc":
        column = "I4"

    while True:
        try:
            return float(sh.sheet1.get(column)[0][0])
        except Exception as e:
            log(f"Fetching from google sheets... {e}", end="\r")
            time.sleep(2)
