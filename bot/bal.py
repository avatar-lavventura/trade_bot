#!/usr/bin/env python3

import asyncio
import time
from contextlib import suppress

import ccxt.async_support as ccxt  # noqa: E402
import gspread
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, _timestamp

from bot.config import config
from bot.sheets_lib import fetch_withdrawn

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})

_log.IS_WRITE = False
gc = gspread.service_account()
sh = gc.open("guncel_kendime_olan_borclar")
WITHDRAWN = fetch_withdrawn(sh)

goal = 0
EKLEME = 0


def f2(value):
    return format(value, ".2f")


async def main():
    max_in_run = 0
    max_val = 0
    if goal > 0:
        max_val = goal

    while True:
        start = ""
        bal_brave = config.total_balance("usdt")
        bal_chrome = config.total_balance("btc")
        _sum = int(bal_brave + bal_chrome + WITHDRAWN - EKLEME)
        if _sum > max_val:
            max_val = _sum

        if _sum > max_in_run and max_in_run != 0:
            start = "[green]*****"

        max_in_run = _sum
        log(f"{_date(_type='hour')} | ", end="")
        c1 = "green on black blink"
        chrome_spot_balance = int(float(config.env["btc"].estimated_balance.find_one("only_usdt")["value"]))
        if chrome_spot_balance > 1000:
            _str = f"{f2(bal_brave)} , {f2(bal_chrome)} ([{c1}]${chrome_spot_balance}[/{c1}]) => {_sum} | [ib]{max_val}"
        else:
            _str = f"{int(bal_brave)} , {int(bal_chrome)} => {_sum} | [ib]{max_val}"

        if goal == 0:
            log(f"{_str} {start}", "b")
        else:
            log(f"{_str} | [ib]{max_val}  {max_in_run} {start}", "b")

        with suppress(Exception):
            sh.sheet1.update("A20:D20", [[_timestamp(), int(bal_brave), int(bal_chrome), _sum]])

        time.sleep(15)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
