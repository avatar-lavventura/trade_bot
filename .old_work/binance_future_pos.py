#!/usr/bin/env python3

import asyncio
from pathlib import Path

import ccxt.async_support as ccxt
from broker._utils.tools import log
from broker._utils.yaml import Yaml

from bot.binance_balances import BotHelperAsync
from bot.trade import BotHelper
from bot.user_setup import check_binance_obj

HOME = Path.home()
_cfg = Yaml(HOME / ".binance.yaml")
api_key = str(_cfg["b"]["key"])
api_secret = str(_cfg["b"]["secret"])
SLEEP_TIME = 15


# exchange_spot.verbose = True  # comment/uncomment for debugging purposes

client, _ = check_binance_obj()
bot = BotHelper(client)


async def close():
    """Close async function.

    https://stackoverflow.com/a/54528397/2402577
    """
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

            log("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", "cyan")
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
