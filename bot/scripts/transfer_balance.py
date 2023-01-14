#!/usr/bin/env python3

import asyncio

from broker._utils._log import log
from broker._utils.tools import print_tb

from bot import config as helper
from bot.bot_helper_async import BotHelperAsync
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import print_tb

bot_async = BotHelperAsync()


async def main():
    try:
        await bot_async.transfer_in(0.06)
    except Exception as e:
        print_tb(e)
    finally:
        await helper.exchange.future.close()
        await helper.exchange.spot.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(bot_async.close())
    except Exception as e:
        print_tb(e)
    finally:
        log("Fin")
