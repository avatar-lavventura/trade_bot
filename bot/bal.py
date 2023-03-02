#!/usr/bin/env python3

import asyncio
import time
from contextlib import suppress

import ccxt.async_support as ccxt  # noqa: E402
import gspread
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, _timestamp

from bot.bot_helper_async import BotHelperAsync
from bot.config import config
from bot.sheets_lib import fetch_withdrawn

_log.IS_WRITE = False
bot_async = BotHelperAsync()
gc = gspread.service_account()
sh = gc.open("guncel_kendime_olan_borclar")
WITHDRAWN = fetch_withdrawn(sh)
goal = 0
goal_btc = 0.125
exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})


async def main():
    max_in_run = 0
    max_val = 0
    if goal > 0:
        max_val = goal

    while True:
        # if config.is_manual_trade:
        #     await bot_async.read_margin_cross_balance()
        start = ""

        # ticker = await exchange.fetch_ticker("BTCUSDT")
        # _goal = int(ticker["last"] * goal_btc)

        bal_brave = config.total_balance("usdt")
        bal_chrome = config.total_balance("btc")
        _sum = int(bal_brave + bal_chrome)
        if _sum > max_val:
            max_val = _sum

        if _sum > max_in_run and max_in_run != 0:
            start = "[green]***********"

        max_in_run = _sum
        log(f"{_date(_type='hour')} | ", end="")

        if goal == 0:
            log(
                f"{int(bal_brave)} , {int(bal_chrome)} => {_sum}  {int(_sum + WITHDRAWN)} | [ib]{max_val} {int(max_val + WITHDRAWN)} {start} ",
                "bold",
            )
        else:
            log(f"{int(bal_brave)} , {int(bal_chrome)} => {_sum} | [ib]{max_val}  {max_in_run} {start}", "bold")

        with suppress(Exception):
            sh.sheet1.update("A20:D20", [[_timestamp(), int(bal_brave), int(bal_chrome), _sum]])

        time.sleep(10)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
