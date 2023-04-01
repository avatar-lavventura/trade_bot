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
WITHDRAWN = fetch_withdrawn(sh, "usdt")
WITHDRAWN_BTC = fetch_withdrawn(sh, "btc")

goal = 0
EKLEME = 0


def f2(value):
    return format(value, ".2f")


async def main():
    max_sum = 0
    max_val = 0
    if goal > 0:
        max_val = goal

    while True:
        BTCUSDT = int(config.prices.find_one("BTCUSDT")["value"])
        start = ""
        bal_brave = config.total_balance("usdt")
        bal_chrome = config.total_balance("btc")
        _sum = int(bal_brave + bal_chrome + WITHDRAWN + (WITHDRAWN_BTC * BTCUSDT) - EKLEME)
        if _sum > max_val:
            max_val = _sum

        if _sum > max_sum and max_sum != 0:
            start = "[green]*****"

        max_sum = _sum
        log(f"{_date(_type='compact')} | ", h=False, end="")
        c1 = "green on black blink"
        chrome_spot_balance = int(float(config.env["btc"].estimated_balance.find_one("only_usdt")["value"]))
        if chrome_spot_balance > 20000:  # over-calculated
            log(f"chrome_spot_balance={chrome_spot_balance} -- overflow")
            time.sleep(20)
            continue

        if chrome_spot_balance > 1000:
            _str = f"{f2(bal_brave)} , {f2(bal_chrome)} ([{c1}]${chrome_spot_balance}[/{c1}]) => {_sum} | [ib]{max_val}"
        else:
            _str = f"{int(bal_brave)} , {int(bal_chrome)} => {_sum} | [ib]{max_val}"

        if goal == 0:
            log(f"{_str} {start}", "b")
        else:
            log(f"{_str} | [ib]{max_val}  {max_sum} {start}", "b")

        with suppress(Exception):
            sh.sheet1.update("A20:D20", [[_timestamp(), int(bal_brave), int(bal_chrome), _sum]])

        time.sleep(20)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
