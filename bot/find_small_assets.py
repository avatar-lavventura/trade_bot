#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils.tools import print_tb

from bot import helper


async def btc():
    """List smaller BTC assets than 0.000004 for blacklist."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_btc
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if asset not in [
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
        ]:
            with suppress(Exception):
                _price = await exchange.fetch_ticker(f"{asset}/BTC")
                _price = _price["last"]
                if float(_price) < 0.001:
                    count += 1
                    print(f":{asset}BTC")

    print(count)


async def usdt():
    """List smaller USDT assets than 0.001 for blacklist."""
    helper.exchange.init_both()
    exchange = helper.exchange.spot_usdt
    assets = await exchange.fetch_balance()
    count = 0
    for asset in assets:
        if (
            asset
            not in [
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
            and "DOWNUSDT" not in f"{asset}USDT"
            and "UPUSDT" not in f"{asset}USDT"
        ):
            with suppress(Exception):
                _price = await exchange.fetch_ticker(f"{asset}/USDT")
                p = _price["previousClose"]
                if float(p) < 0.02:
                    count += 1
                    print(f":{asset}USDT")

    print()
    print(count)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        # loop.run_until_complete(btc())
        loop.run_until_complete(usdt())
    except Exception as e:
        print_tb(e)
