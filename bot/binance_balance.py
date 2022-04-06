#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils._async import _sleep
from broker._utils._log import log
from broker._utils.tools import _exit, delete_multiple_lines, print_tb
from broker.errors import QuietExit
from broker.libs.math import _percent
from ccxt.base.errors import RequestTimeout  # NOQA

from bot import cfg, helper
from bot.binance_futures import future_stats, futures_bal, process_future_positions
from bot.bot_helper_async_usdt import BotHelperSpotAsync
from bot.config import config
from bot.spot_lib import update_spot_timestamp

RUN_FUTURES = False
bot_async = BotHelperSpotAsync()


async def alert():
    for alert in config.ALERTS:
        _alert = config.ALERTS[alert]
        if _alert:
            asset_price = await bot_async.spot_fetch_ticker(_alert["pair"])
            if float(asset_price) > _alert["price"]:
                await bot_async.channel_alerts.send(f"{_alert['pair']}={asset_price}", delete_after=cfg.SLEEP_INTERVAL)


async def process(unix_timestamp_ms):
    update_spot_timestamp(unix_timestamp_ms)  # first update spot timestamps
    *_, usdt_bal, free_usdt, free_btc = await bot_async.spot_balance()
    if usdt_bal > 0.125 and not helper.is_start:
        log()

    if RUN_FUTURES:
        bot_async.futures_balance = await helper.exchange.future.fetch_balance()
        unix_timestamp_ms = helper.exchange.get_future_timestamp()
        config.status["root"][cfg.TYPE]["free"] = futures_bal("free", "USDT") + usdt_bal

        usdt_bal += futures_bal("total", "USDT") + futures_bal("total", "BUSD")
    else:
        if cfg.TYPE.lower() == "usdt":
            config.env[cfg.TYPE].status["balance"] = usdt_bal
            config.env[cfg.TYPE].status["free"] = free_usdt

        if cfg.TYPE.lower() == "btc":
            config.env[cfg.TYPE].status["free"] = "{:.8f}".format(free_btc)

    for idx in range(1, 6):
        config.env[cfg.TYPE].risk[f"{idx}_per"] = _percent(config.env[cfg.TYPE].status["balance"], idx)

    if RUN_FUTURES:
        positions = await helper.exchange.future.fetch_positions()
        is_printed = await process_future_positions(positions, usdt_bal, unix_timestamp_ms, bot_async.channel)
        if not is_printed and not helper.is_start and config.status_usdt["count"] == 0:
            delete_multiple_lines(2)

        if not is_printed or helper.is_start:
            future_stats(usdt_bal, unix_timestamp_ms)
            helper.is_start = False
    elif helper.is_start and config.status_usdt["count"] == 0:
        delete_multiple_lines(1)

    if cfg.TYPE == "usdt":
        await alert()


async def process_main(obj):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    bot_async.channel = obj.channel
    bot_async.channel_alerts = obj.channel_alerts
    config.reload()
    try:
        if not RUN_FUTURES:
            unix_timestamp_ms = helper.exchange.get_spot_timestamp()

        await process(unix_timestamp_ms)
    except RequestTimeout:
        _exit("Timestamp for this request is outside of the recieve_window=5000")
    except KeyError as e:
        print_tb(e)
        _exit("KeyError")
    except Exception as e:
        if "quantity is zero" in str(e):
            log(f"#> {e} [green]don't worry")
        elif "Timestamp for this request is outside of the recvWindow" in str(e):
            log("E: Timestamp for this request is outside of the recvWindow")
        else:
            print_tb(e)
            await _sleep(30)


async def main():
    await helper.exchange.set_markets()
    while True:
        try:
            await process_main(bot_async)
            await _sleep(22)
        except KeyboardInterrupt:
            break
        except Exception as e:
            if "Timestamp for this request is outside of the recvWindow" in str(e):
                log(f"E: {e}")
            else:
                print_tb(e)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())
    except QuietExit as e:
        if e:
            log(str(e))
    except Exception as e:
        print_tb(e)
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())
