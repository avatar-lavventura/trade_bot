#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils.tools import print_tb

from bot import helper
from bot.lib import ignore_list


async def btc_search():
    """List smaller BTC assets than 0.000004 for blacklist."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_btc
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if asset not in ignore_list:
            with suppress(Exception):
                price = await exchange.fetch_ticker(f"{asset}BTC")
                price = price["last"]
                if 0 < float(price) < 0.000002:
                    count += 1
                    print(f":{asset}BTC")

    print(count)
    await exchange.close()


async def usdt_search():
    """List smaller USDT assets than 0.06 for blacklist_usdt.txt."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_usdt
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if asset not in ignore_list and "DOWNUSDT" not in f"{asset}USDT" and "UPUSDT" not in f"{asset}USDT":
            with suppress(Exception):
                price = await exchange.fetch_ticker(f"{asset}USDT")
                price = price["previousClose"]
                if 0 < float(price) < 0.06:  # was: 0.02
                    count += 1
                    print(f":{asset}USDT")

    # print(f"count={count}")
    await exchange.close()


def main():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(btc_search())
        print()
        loop.run_until_complete(usdt_search())
    except Exception as e:
        print_tb(e)


if __name__ == "__main__":
    main()
