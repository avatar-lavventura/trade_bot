#!/usr/bin/env python3

import asyncio

import ccxt.async_support as ccxt  # noqa: E402
from broker._utils._async import _sleep
from broker._utils._log import log


async def main(symbol):
    should_be = 3000
    repay = 4213
    amount = 1212
    # you can set enableRateLimit = True to enable the built-in rate limiter
    # this way you request rate will never hit the limit of an exchange
    # the library will throttle your requests to avoid that
    #
    # __ https://docs.ccxt.com/en/latest/ccxt.pro.manual.html#exchanges
    _delta = 0
    flag = False
    exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
    while True:
        # print('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')
        # print(exchange.iso8601(exchange.milliseconds()), 'fetching', symbol, 'ticker from', exchange.name)
        # this can be any call instead of fetch_ticker, really
        try:
            LQTYBTC = await exchange.fetch_ticker("LQTYBTC")
            BTCUSDT = await exchange.fetch_ticker("BTCUSDT")
            ticker = await exchange.fetch_ticker(symbol)

            now = int(LQTYBTC["last"] * BTCUSDT["last"] * amount)
            # trades = await exchange.fetch_trades(symbol)
            # log(trades)
            # print(exchange.iso8601(exchange.milliseconds()), 'fetched', symbol, 'ticker from', exchange.name)
            if not flag:
                log(ticker)
                flag = True

            _last = ticker["last"]
            eq = 3588 * _last - repay + 103
            if int(eq) < 0:
                log(f"[red]{int(eq)}[/red]      ---      {_last}    -- should be: {should_be}", is_write=False)
            else:
                delta = int(eq - now)
                _str = ""
                if delta > _delta:
                    _delta = delta
                    _str = "***********"

                if delta < 0:
                    delta_str = f"[red]{delta}[/red]"
                else:
                    delta_str = f"[g]+{delta}[/g]"

                log(
                    f"{int(eq)}  {now}  {delta_str}        {_last}     -- should be: {should_be} [g]{_str}",
                    is_write=False,
                )

            await _sleep(3)
        except Exception:
            print("sleeping for 60 seconds...")
            await _sleep(60)
            print("[  ok  ]")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main("LQTYUSDT"))
