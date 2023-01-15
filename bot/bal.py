#!/usr/bin/env python3

import time

from broker._utils.tools import _date

from bot.config import config


def main():
    while True:
        bal1 = float(config.env["usdt"].estimated_balance.find_one("total_balance")["value"])
        bal2 = float(config.env["btc"].estimated_balance.find_one("total_balance")["value"])
        print(f"{_date(_type='hour')} | ", end="")
        print(f"{int(bal1)} + {int(bal2)} => {int(bal1 + bal2)}", end="")
        #
        b1 = 2450
        b2 = 4500
        print(f"         2450 + 4500 => {b1 + b2}")
        time.sleep(10)


if __name__ == "__main__":
    main()
