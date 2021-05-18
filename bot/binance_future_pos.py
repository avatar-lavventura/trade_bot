#!/usr/bin/env python3

import asyncio
import os
from pathlib import Path

import ccxt.async_support as ccxt  # noqa: E402
from broker._utils.tools import _colorize_traceback, get_decimal_count, log
from broker.libs.math import percent_change

from bot.binance_balances import BotHelperAsync
from bot.trade import BotHelper
from bot.user_setup import check_binance_obj

HOME = str(Path.home())
TP = 0.005
TAKE_PROFIT_LONG = 1.000 + TP
TAKE_PROFIT_SHORT = 1.000 - TP

_file = f"{HOME}/.binance.txt"
if not os.path.exists(_file):
    with open(_file, "w"):
        pass

file1 = open(_file, "r")
Lines = file1.readlines()
api_key = str(Lines[0].strip())
api_secret = str(Lines[1].strip())
SLEEP_TIME = 15
PERCENT_CHANGE_TO_ADD_FUTURES = -5.0
PERCENT_CHANGE_TO_ADD = -5.0


# exchange_spot.verbose = True  # comment/uncomment for debugging purposes

client, _ = check_binance_obj()
bot = BotHelper(client)


async def close():
    """doc: https://stackoverflow.com/a/54528397/2402577"""
    log("Finalazing...")
    await asyncio.sleep(1)


async def main():
    bot = BotHelperAsync()
    while True:
        try:
            futures = await bot.exchange_future.fetch_balance()
            for future in futures["info"]["positions"]:
                if float(future["positionAmt"]) != 0.0:
                    print(future["symbol"])
                    break

            log("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            await asyncio.sleep(SLEEP_TIME)  # https://stackoverflow.com/a/61764275/2402577
            # await exchange_future.close()
            # await exchange_spot.close()
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
            # break  # won't retry


if __name__ == "__main__":
    # await exchange_spot.load_markets()
    # await exchange_future.load_markets()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(close())
    finally:
        print("Program finished")
