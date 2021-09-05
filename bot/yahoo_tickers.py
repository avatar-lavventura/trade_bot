#!/usr/bin/env python3

import asyncio

from _mongodb import Mongo
from pymongo import MongoClient

from bot.config import config
from bot.my_balance import fetch_balance, get_silver
from ebloc_broker.broker._utils.tools import _colorize_traceback, _timestamp, log

mc = MongoClient()
mongoDB = Mongo(mc, mc["trader_bot"]["timestamp"])


async def main():
    time_now = _timestamp()
    total_balance = await fetch_balance()
    silver_gr = config.config["portfolio"]["SILVER"]["gr"]
    silver_usdt = float(format(get_silver(silver_gr), ".2f"))
    config.config["portfolio"]["SILVER"]["troy_ounce"] = silver_gr * 0.032151
    log(f" * Silver => {silver_usdt}")
    config.config["portfolio"]["SILVER"]["USD"] = silver_usdt
    # total_balance = total_balance + silver_usdt
    total_balance = format(total_balance, ".2f")
    config.config["portfolio"]["_TOTAL"] = float(total_balance)
    log(f"total_balance={total_balance}")
    mongoDB.add_item(time_now, config.config["portfolio"])
    log("SUCCESS")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        _colorize_traceback(e)
