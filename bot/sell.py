#!/usr/bin/env python3

import asyncio

from broker._utils._log import log
from broker._utils.tools import print_tb

from bot.bot_helper_async import BotHelperAsync
from bot.trade_async import BotHelper
from bot.user_setup import check_binance_obj

# from bot import config as helper

client, _ = check_binance_obj()
bot = BotHelper(client)
bot_async = BotHelperAsync()


# async def sell_order():
#     try:
#         own_usdt, future_balance = await bot_async.spot_balance(is_limit=False)
#     except Exception as e:
#         print_tb(e)
#     finally:
#         await helper.exchange.future.close()
#         await helper.exchange.spot.close()


# async def main():
#     """Start fetching balance."""
#     await sell_order()


async def main():
    pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(bot_async.close())
    except Exception as e:
        print_tb(e)
    finally:
        log("Program finished.", "bold green")
