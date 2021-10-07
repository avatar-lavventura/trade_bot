#!/usr/bin/env python3

from bot import helper
import asyncio
from ebloc_broker.broker._utils.tools import print_tb
from ebloc_broker.broker._utils._log import log
from bot_helper_async import BotHelperAsync

bot_async = BotHelperAsync()

async def main():
    # __ https://github.com/ccxt/ccxt/issues/10169#issuecomment-937605731
    await bot_async.transfer_out(10)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(helper.exchange.close())
    except Exception as e:
        print_tb(e)
    finally:
        log("Program finished.", "bold green")
