#!/usr/bin/env python3

import asyncio

from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import print_tb

from bot import helper
from bot.bot_helper_async import BotHelperAsync

bot_async = BotHelperAsync()


async def main():
    future_positions = await helper.exchange.future.fetch_positions()
    for position in future_positions:
        initial_margin = abs(float(position["info"]["isolatedWallet"]))
        if initial_margin > 0.0:
            print(position)


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
