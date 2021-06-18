#!/usr/bin/env python3

import asyncio

import ccxt.async_support as ccxt  # noqa: E402

# https://github.com/ccxt/ccxt/tree/master/examples/py
INITIAL_BTC_QTY = 0.0002
SLEEP_TIME = 1


async def main(symbol, default_type):
    # you can set enableRateLimit = True to enable the built-in rate limiter
    # this way you request rate will never hit the limit of an exchange
    # the library will throttle your requests to avoid that

    flag = False
    exchange = ccxt.binance(
        {
            "options": {"default_type": default_type},
            "enableRateLimit": True,  # this option enables the built-in rate limiter
        }
    )
    while True:
        # print('--------------------------------------------------------------')
        # print(exchange.iso8601(exchange.milliseconds()), 'fetching', symbol, 'ticker from', exchange.name)
        # this can be any call instead of fetch_ticker, really
        try:
            ticker = await exchange.fetch_ticker(symbol)
            # print(exchange.iso8601(exchange.milliseconds()), 'fetched', symbol, 'ticker from', exchange.name)
            if not flag:
                print(ticker)
                flag = True
            print(ticker["last"])
            print(INITIAL_BTC_QTY / float(ticker["last"]))
            await asyncio.sleep(SLEEP_TIME)  # https://stackoverflow.com/a/61764275/2402577
        except ccxt.RequestTimeout as e:
            print("[" + type(e).__name__ + "]")
            print(str(e)[0:200])
            # will retry
        except ccxt.DDoSProtection as e:
            print("[" + type(e).__name__ + "]")
            print(str(e.args)[0:200])
            # will retry
        except ccxt.ExchangeNotAvailable as e:
            print("[" + type(e).__name__ + "]")
            print(str(e.args)[0:200])
            # will retry
        except ccxt.ExchangeError as e:
            print("[" + type(e).__name__ + "]")
            print(str(e)[0:200])
            break  # won't retry


# symbol = "NEO/USDT"
symbol = "NEO/BTC"
symbol = "BTC/USDT"
asyncio.get_event_loop().run_until_complete(main(symbol, "spot"))
