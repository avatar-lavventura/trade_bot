#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils.tools import print_tb

from bot import helper

ignore_list = [
    "BTC",
    "info",
    "LTC",
    "ETH",
    "timestamp",
    "datetime",
    "free",
    "used",
    "total",
    "USDT",
    "IQ",
    "VTHO",
]


async def btc():
    """List smaller BTC assets than 0.000004 for blacklist."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_btc
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if asset not in ignore_list:
            with suppress(Exception):
                price = await exchange.fetch_ticker(f"{asset}/BTC")
                price = price["last"]
                if 0 < float(price) < 0.000002:
                    count += 1
                    print(f":{asset}BTC")

    print(count)
    await exchange.close()


async def usdt():
    """List smaller USDT assets than 0.06 for blacklist.txt."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_usdt
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if asset not in ignore_list and "DOWNUSDT" not in f"{asset}USDT" and "UPUSDT" not in f"{asset}USDT":
            with suppress(Exception):
                price = await exchange.fetch_ticker(f"{asset}/USDT")
                price = price["previousClose"]
                if 0 < float(price) < 0.06:  # was: 0.02
                    count += 1
                    print(f":{asset}USDT")

    print()
    print(f"count={count}")
    await exchange.close()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(btc())
        print()
        loop.run_until_complete(usdt())
    except Exception as e:
        print_tb(e)
