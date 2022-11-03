#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils import _log
from broker._utils._log import log
from pymongo import MongoClient

from bot import helper
from bot.mongodb import Mongo

_log.IS_WRITE = False


async def main():
    mc = MongoClient()
    for symbol in ["btc"]:
        mongo = Mongo(mc, mc[symbol]["stats"])
        cursor = mongo.find_all(sort_str="timestamp", is_return=True)
        if cursor:
            log(f" * {symbol}")

            for document in cursor:
                log(document)

            print()

    total_balance = {}
    for symbol in ["usdt", "btc"]:
        mongo = Mongo(mc, mc[symbol]["balance"])
        output = mongo.find_all(sort_str="timestamp", is_return=True)
        mongo.find_all(sort_str="timestamp")
        for item in output:
            _key = item["key"]
            if _key not in total_balance:
                total_balance[_key] = 0

            with suppress(Exception):
                total_balance[_key] += float(item["value"]["usdt"])

    for symbol in total_balance:
        total_balance[symbol] = round(total_balance[symbol])

    log(dict(total_balance))

    # mongo = Mongo(mc, mc["btc"]["hit"])
    # mongo.find_all(sort_str="value")
    # print()

    # print()
    # for symbol in ["usdt", "btc"]:
    #     mongo = Mongo(mc, mc[symbol]["status"])
    #     output = mongo.find_one("count")["value"]
    #     print(f"pos_count_{symbol}={output}")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
