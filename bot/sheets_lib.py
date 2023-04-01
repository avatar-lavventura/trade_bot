#!/usr/bin/env python3

import time


def fetch_withdrawn(sh, asset) -> float:
    column = ""
    if asset == "usdt":
        column = "L2"
    elif asset == "btc":
        column = "I4"

    while True:
        try:
            return float(sh.sheet1.get(column)[0][0])
        except:
            time.sleep(2)
