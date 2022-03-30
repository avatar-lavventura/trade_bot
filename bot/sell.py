#!/usr/bin/env python3

import asyncio
import math
import yfinance as yf
from broker._utils._async import _sleep
from broker._utils._log import log
from broker._utils.tools import _date, print_tb
from contextlib import suppress

from bot import helper
from bot.bot_helper_async import BotHelperAsync
from bot.config import config
from bot.trade_async import BotHelper
from bot.user_setup import check_binance_obj

client, _ = check_binance_obj()
bot = BotHelper(client)
bot_async = BotHelperAsync()


async def sell_order():
    total_balance = 0.0
    try:
        own_usd, future_balance = await bot_async.spot_balance(is_limit=False)
    except Exception as e:
        print_tb(e)
    finally:
        await helper.exchange.future.close()
        await helper.exchange.spot.close()


async def main():
    """Start fetching balance."""
    await sell_order()


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
