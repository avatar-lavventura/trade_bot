#!/usr/bin/env python3

import time
import asyncio
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date
from bot.bot_helper_async import BotHelperAsync

from bot.config import config

_log.IS_WRITE = False
bot_async = BotHelperAsync()


async def main():
    max_val = 8600
    while True:
        # if config.trade_mode:
        #     await bot_async.read_margin_cross_balance()

        bal_brave = float(config.env["usdt"].estimated_balance.find_one("total_balance")["value"])
        bal_chrome = float(config.env["btc"].estimated_balance.find_one("total_balance")["value"])
        _sum = int(bal_brave + bal_chrome)
        if _sum > max_val:
            max_val = _sum

        log(f"{_date(_type='hour')} | ", end="")
        log(f"{int(bal_brave)} + {int(bal_chrome)} => {_sum} | max=[italic black]{max_val}", "bold")
        time.sleep(10)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
