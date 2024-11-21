#!/usr/bin/env python3

import asyncio
from contextlib import suppress

from _utils._async import _sleep
from _utils._log import log
from _utils.tools import _date, _sys_exit, delete_multiple_lines, print_tb
from errors import QuietExit
from libs.math import _percent
from ccxt.base.errors import RequestTimeout

import cfg
import config as helper
from bot_helper_async_usdt import BotHelperSpotAsync
from config import config
from spot_lib import update_spot_timestamps

# from bot.futures.binance_futures import futures_bal

IS_FUTURES = False
bot_async = BotHelperSpotAsync()


async def is_rapid_alert(msg, alert):
    if "rapid_alert" in alert and alert["rapid_alert"] == "on":
        for _ in range(1, 10):
            await bot_async.channel_alerts.send(msg, delete_after=0.1)
            await asyncio.sleep(0.1)


async def discord_send_alert():
    #: TODO: check this also for brave-btc?
    if len(config._c["alert_if_position_closed"]) > 0:
        for symbol in cfg.BALANCES:
            if symbol not in cfg.ignore_list and cfg.BALANCES[symbol]["total"] == 0:
                if symbol in config._c["alert_if_position_closed"]:
                    msg = f"{symbol} is closed :beer:"
                    await bot_async.channel_alerts.send(msg, delete_after=cfg.SLEEP_INTERVAL)
                    config._c["alert_if_position_closed"].remove(symbol)
                    config.cfg.dump()

    alert_track = {}
    asset_price_dict = {}
    alert_key = "greater_than"
    for alert_key in ["greater_than", "less_than"]:
        for idx in config.ALERTS[alert_key]:
            alert = config.ALERTS[alert_key][idx]
            _pair = alert["pair"]
            asset_price_dict[_pair] = _asset_price = await bot_async.spot_fetch_ticker(_pair)
            if _asset_price == 0:
                log("warning: asset_price is 0, something is wrong")
                return

            if (alert_key == "greater_than" and float(_asset_price) >= alert["price"]) or (
                alert_key == "less_than" and float(_asset_price) <= alert["price"]
            ):
                if _pair[-3:] == "BTC":
                    asset = _pair[:-3]
                    _asset_price = format(_asset_price * 1000, ".5")
                elif _pair[-4:] == "USDT":
                    asset = _pair[:-4]
                elif _pair[-4:] == "BUSD":
                    asset = _pair[:-4]

                if asset not in alert_track:  #: allows only 1 alert per asset
                    await is_rapid_alert(f"{_pair}={_asset_price}\nAlper, wakeup !!! IMPORTANT !!!", alert)
                    msg = f"{_pair}={_asset_price} {_date(_type='compact')} Alper, wakeup."
                    # https://discordpy.readthedocs.io/en/neo-docs/api.html#discord.abc.Messageable.send
                    await bot_async.channel_alerts.send(msg, delete_after=cfg.SLEEP_INTERVAL)
                    alert_track[asset] = True


async def clean_for_new_cycle() -> None:
    cfg.PRICES = {}
    cfg.PRICES["BTCUSDT"] = await bot_async.spot_fetch_ticker("BTCUSDT")
    config.prices.add_single_key("BTCUSDT", int(cfg.PRICES["BTCUSDT"]))
    # TODO: store this at mongoDB along with its ts


async def process(unix_timestamp_ms):
    """Start iteration to analyze open positions."""
    try:
        await clean_for_new_cycle()
        update_spot_timestamps(unix_timestamp_ms)  # current ts is saved
        *_, usdt_bal, free_usdt, free_btc = await bot_async.spot_balance()
        if cfg.TYPE == "usdt":
            config.env[cfg.TYPE].status["balance"] = usdt_bal
            config.env[cfg.TYPE].status["free"] = free_usdt
        elif cfg.TYPE == "btc":
            config.env[cfg.TYPE].status["free"] = float(format(free_btc, ".8f"))
        elif cfg.TYPE == "bybit":
            config.env[cfg.TYPE].status["balance"] = usdt_bal
            config.env[cfg.TYPE].status["free"] = free_usdt

        for idx in range(1, 6):
            config.env[cfg.TYPE].risk[f"{idx}_per"] = _percent(config.env[cfg.TYPE].status["balance"], idx)

        pos_count = config.env[cfg.TYPE]._status.find_one("count")["value"]
        if pos_count == 0:
            print("")
            delete_multiple_lines(2)  # delete_lines
    except Exception as e:
        print_tb(e)
        raise e


async def process_main(obj):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    try:
        bot_async.channel = obj.channel
        bot_async.channel_log = obj.channel_log
        bot_async.channel_alerts = obj.channel_alerts
        config._reload()
        unix_timestamp_ms = helper.exchange.get_spot_timestamp()
        await process(unix_timestamp_ms)
    except RequestTimeout:
        _sys_exit("E: Timestamp for this request is outside of the recieve_window=5000")
    except KeyError as e:
        print_tb(e)
        _sys_exit("KeyError")  # helps to restart the process
    except Exception as e:
        if "quantity is zero" in str(e):
            log(f"==> {e} [green]don't worry")
        elif "Timestamp for this request is outside of the recvWindow" in str(e):
            log("warning: timestamp for this request is outside of the recvWindow")
        else:
            print_tb(e)
            await _sleep(30)

    if cfg.TYPE == "usdt":
        await discord_send_alert()


async def main():
    await helper.exchange.set_markets()
    while True:
        try:
            await process_main(bot_async)
            await _sleep(cfg.SLEEP_INTERVAL + 2)
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
