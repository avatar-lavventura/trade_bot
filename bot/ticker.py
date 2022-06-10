#!/usr/bin/env python3

import asyncio

import ccxt.async_support as ccxt  # noqa: E402
from broker._utils._async import _sleep
from broker._utils._log import log
from broker._utils.tools import print_tb


async def main(symbol):
    # you can set enableRateLimit = True to enable the built-in rate limiter
    # this way you request rate will never hit the limit of an exchange
    # the library will throttle your requests to avoid that
    flag = False
    exchange = ccxt.binanceusdm({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
    while True:
        # print('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')
        # print(exchange.iso8601(exchange.milliseconds()), 'fetching', symbol, 'ticker from', exchange.name)
        # this can be any call instead of fetch_ticker, really
        try:
            ticker = await exchange.fetch_ticker(symbol)
            # trades = await exchange.fetch_trades(symbol)
            # log(trades)
            # print(exchange.iso8601(exchange.milliseconds()), 'fetched', symbol, 'ticker from', exchange.name)
            if not flag:
                log(ticker)
                flag = True

            print(ticker["last"])
            await _sleep()
        except Exception as e:
            print_tb(e)
            break


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main("BTCUSDT"))
