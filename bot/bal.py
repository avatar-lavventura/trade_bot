#!/usr/bin/env python3

import time

from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date

from bot.config import config

_log.IS_WRITE = False


def main():
    max_val = 7348
    while True:
        bal1 = float(config.env["usdt"].estimated_balance.find_one("total_balance")["value"])
        bal2 = float(config.env["btc"].estimated_balance.find_one("total_balance")["value"])
        _sum = int(bal1 + bal2)
        if _sum > max_val:
            max_val = _sum

        log(f"{_date(_type='hour')} | ", end="")
        log(f"{int(bal1)} + {int(bal2)} => {_sum}                    max=[italic black]{max_val}", "bold")
        time.sleep(10)


if __name__ == "__main__":
    main()
