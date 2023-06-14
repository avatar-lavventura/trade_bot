#!/usr/bin/env python3

import asyncio
import time
from contextlib import suppress

import ccxt.async_support as ccxt  # noqa: E402
import gspread
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, _timestamp, print_tb

from bot.config import config
from bot.sheets_lib import fetch_withdrawn

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})

_log.IS_WRITE = True
# _log.ll.LOG_FILENAME = "bal.log"
gc = gspread.service_account()
sh = gc.open("guncel_kendime_olan_borclar")

goal = 0
EKLEME = 0


def f2(value):
    return format(value, ".2f")


async def process(max_sum, max_val):
    WITHDRAWN_USDT, TRBINANCE_BTC, TRBINANCE_USDT = fetch_withdrawn(sh)
    BTCUSDT = int(config.prices.find_one("BTCUSDT")["value"])
    start = ""
    bal_brave = config.total_balance("usdt") + TRBINANCE_USDT
    bal_chrome = config.total_balance("btc")
    _sum = int(bal_brave + bal_chrome + WITHDRAWN_USDT + (TRBINANCE_BTC * BTCUSDT) - EKLEME)
    all_btc_asset = format(float(config.env["btc"].balance_sum.find_one("usdt")["value"]) / BTCUSDT, ".8f")

    max_sum = _sum
    max_sum = _sum = int(0.21439941 * BTCUSDT + (1576 + 1000 + 500 + 1000 + 500 - 80 - 5))  # delete_me
    """ uncomment_me
    if _sum > max_sum and max_sum != 0 and not start:
        start = "[green]*****"
    """
    log(f"[cy]<{_date(_type='compact')}>[/cy] ", h=False, end="")
    c1 = "green on black blink"
    chrome_spot_balance = int(float(config.env["btc"].estimated_balance.find_one("only_usdt")["value"]))
    if chrome_spot_balance > 20000:  # over-calculated
        log(f"chrome_spot_balance={chrome_spot_balance} => overflow")
        time.sleep(20)
        return

    hot_sum = f2(bal_brave + bal_chrome)
    if float(hot_sum) > max_val:
        max_val = float(hot_sum)
        start = "[blue]*****"
    else:
        start = ""

    hot_btc_sum = format(TRBINANCE_BTC + float(all_btc_asset), ".8f")

    if all_btc_asset == 0:
        _str = f"[w][{TRBINANCE_BTC}][/w] |"
    else:
        if all_btc_asset != hot_btc_sum:
            _str = f"[w][{TRBINANCE_BTC} + {all_btc_asset} => {hot_btc_sum}][/w]"
        else:
            _str = f"[w]{hot_btc_sum}[/w]"

    if bal_brave > 1.0:
        if chrome_spot_balance > 500:
            _str = f" | {_str} {f2(bal_brave)} , {f2(bal_chrome)} ([{c1}]${chrome_spot_balance}[/{c1}])"
        else:
            _str = f" | {_str} {int(bal_brave)} , {int(bal_chrome)}"

    _str = f"{_str} => [[orange]{hot_sum}[/orange] [green]{_sum}[/green]] [ib]{max_val}"
    if goal == 0:
        log(f"{_str} {start}")
    else:
        log(f"{_str} | [ib]{max_val}  {max_sum} {start}")

    with suppress(Exception):
        sh.sheet1.update("A20:D20", [[_timestamp(), int(bal_brave), int(bal_chrome), _sum]])

    time.sleep(19)
    return max_val


async def main():
    max_sum = 0
    max_val = 0
    if goal > 0:
        max_val = goal

    while True:
        max_val = await process(max_sum, max_val)


async def close():
    """Close async program.

    https://stackoverflow.com/a/54528397/2402577
    """
    log("Finalizing...")
    await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        with suppress(Exception):
            loop.run_until_complete(close())
    except Exception as e:
        print_tb(e)
