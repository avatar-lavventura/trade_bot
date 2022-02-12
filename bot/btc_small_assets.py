#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from bot import helper
from ebloc_broker.broker._utils.tools import print_tb


async def main():
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
                if float(_price) < 0.000004:
                    count += 1
                    print(f":{asset}BTC")

    print(count)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print_tb(e)
