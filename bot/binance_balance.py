#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from broker._utils._async import _sleep
from broker._utils._log import log
from broker._utils.tools import _exit, delete_multiple_lines, print_tb
from broker.errors import QuietExit
from broker.libs.math import _percent
from ccxt.base.errors import RequestTimeout

from bot import cfg, helper
from bot.bot_helper_async_usdt import BotHelperSpotAsync
from bot.config import config
from bot.futures.binance_futures import future_stats, futures_bal, process_future_positions
from bot.spot_lib import update_spot_timestamps

IS_FUTURES = False
bot_async = BotHelperSpotAsync()


async def discord_send_alert():
    asset_price_dict = {}
    for idx in config.ALERTS:
        alert = config.ALERTS[idx]
        asset_price_dict[alert["pair"]] = _asset_price = await bot_async.spot_fetch_ticker(alert["pair"])
        if float(_asset_price) > alert["price"]:
            await bot_async.channel_alerts.send(f"{alert['pair']}={_asset_price}", delete_after=cfg.SLEEP_INTERVAL)


async def process(unix_timestamp_ms):
    update_spot_timestamps(unix_timestamp_ms)
    *_, usdt_bal, free_usdt, free_btc = await bot_async.spot_balance()
    if usdt_bal > 0.125 and not helper.is_start:
        log()

    if IS_FUTURES:
        bot_async.futures_balance = await helper.exchange.future.fetch_balance()
        unix_timestamp_ms = helper.exchange.get_future_timestamp()
        config.status["root"][cfg.TYPE]["free"] = futures_bal("free", "USDT") + usdt_bal
        usdt_bal += futures_bal("total", "USDT") + futures_bal("total", "BUSD")
    elif cfg.TYPE == "usdt":
        config.env[cfg.TYPE].status["balance"] = usdt_bal
        config.env[cfg.TYPE].status["free"] = free_usdt
    elif cfg.TYPE == "btc":
        config.env[cfg.TYPE].status["free"] = float(format(free_btc, ".8f"))

    for idx in range(1, 6):
        config.env[cfg.TYPE].risk[f"{idx}_per"] = _percent(config.env[cfg.TYPE].status["balance"], idx)

    usdt_pos_count = config.env["usdt"]._status.find_one("count")["value"]
    if IS_FUTURES:
        positions = await helper.exchange.future.fetch_positions()
        is_printed = await process_future_positions(positions, usdt_bal, unix_timestamp_ms, bot_async.channel)

        if not is_printed and not helper.is_start and usdt_pos_count == 0 and not cfg.locked_balance > 10:
            delete_multiple_lines(2)

        if not is_printed or helper.is_start:
            future_stats(usdt_bal, unix_timestamp_ms)
            helper.is_start = False
    elif helper.is_start and usdt_pos_count == 0 and not cfg.locked_balance > 10:
        delete_multiple_lines(1)

    if cfg.TYPE == "usdt":
        await discord_send_alert()


async def process_main(obj):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    bot_async.channel = obj.channel
    bot_async.channel_alerts = obj.channel_alerts
    config._reload()
    try:
        if not IS_FUTURES:
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
            log("warning: Timestamp for this request is outside of the recvWindow")
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
                log(f"warning: {e}")
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
