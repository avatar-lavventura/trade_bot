#!/usr/bin/env python3

import asyncio
from contextlib import suppress
from pathlib import Path
from user_setup import check_binance_obj
from bot.bot_helper_async import BotHelperAsync
from ebloc_broker.broker._utils.tools import log, _colorize_traceback
from ebloc_broker.broker._utils._async import _sleep
HOME = str(Path.home())
bot_async = BotHelperAsync()


async def main():
    """Set levereage for USDT and BUSD."""
    await bot_async._load_markets()
    client, _ = check_binance_obj()
    futures = client.futures_position_information()
    for future in futures:
        symbol = future["symbol"].replace("USDT", "/USDT").replace("BUSD", "/BUSD")
        if "USDT_" not in symbol and symbol not in ["BTCST/USDT"]:
            await bot_async.set_leverage(symbol)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())
    except Exception as e:
        _colorize_traceback(e)
        _sleep(120)
        loop.run_until_complete(main())
    finally:
        log("Program finished.", "green")
        loop.run_until_complete(bot_async.close())
