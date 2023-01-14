#!/usr/bin/env python3

import asyncio

from broker._utils._log import log
from broker._utils.tools import _timestamp, print_tb
from pymongo import MongoClient

from bot.config import config
from bot.mongodb import Mongo
from bot.usdtperp.my_balance import get_gold, get_silver

mc = MongoClient()
mongo_db = Mongo(mc, mc["trader_bot"]["timestamp"])


async def main_async():
    time_now = _timestamp()
    total_balance = 0
    silver_gr = float(config.goal["portfolio"]["SILVER"]["gr"])
    if silver_gr > 0.0:
        silver_usdt = float(format(get_silver(silver_gr), ".2f"))
        config.goal["portfolio"]["SILVER"]["troy_ounce"] = silver_gr * 0.032151
        log(f" * Silver => {silver_usdt}")
        config.goal["portfolio"]["SILVER"]["USD"] = silver_usdt

    gold_gr = config.goal["portfolio"]["GOLD"]["gr"]
    if gold_gr > 0.0:
        gold_usdt = float(format(get_gold(gold_gr), ".2f"))
        config.goal["portfolio"]["GOLD"]["troy_ounce"] = float(format(gold_gr * 0.032151, ".4f"))
        log(f" * [yellow]gold[/yellow] => {gold_usdt}")
        config.goal["portfolio"]["GOLD"]["USD"] = gold_usdt

    # total_balance = total_balance + silver_usdt
    total_balance = format(total_balance, ".2f")
    config.goal["portfolio"]["_TOTAL"] = float(total_balance)
    log(f"total_balance={total_balance} | {time_now}")
    # mongo_db.add_item(time_now, config.goal["portfolio"])


def main():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main_async())
    except Exception as e:
        print_tb(e)


if __name__ == "__main__":
    main()
