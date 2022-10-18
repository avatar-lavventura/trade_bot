#!/usr/bin/env python3

import logging
import os
import sys
from contextlib import suppress
from pathlib import Path

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, print_tb
from broker._utils.yaml import Yaml

from bot import binance_balance, cfg, helper
from bot.binance_balance import process_main
from bot.config import config

logging.disable(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("apscheduler.executors.default").propagate = False


class Discord_Alpy:
    def __init__(self, _type):
        try:
            if config.cfg["root"]["is_write"]:
                _log.ll.LOG_FILENAME = Path.home() / ".bot" / "program.log"
            else:
                _log.IS_WRITE = False

            log(f"[cyan]**[/cyan] bot_type={_type} mode started [cyan]**", "bold")
            self._type = cfg.TYPE = _type.lower()
            helper.exchange.init(_type)
            _config = Yaml(Path.home() / ".binance.yaml")
            self.client = discord.Client()
            self.channel: str = ""
            self.channel_alerts: str = ""
            self.channel_name = str(_config["discord"]["CHANNEL_NAME"])
            self.TOKEN = str(_config["discord"]["TOKEN"])
            self.client.loop.create_task(self.task())
            self.client.loop.run_until_complete(self.client.start(self.TOKEN))
        except KeyboardInterrupt:
            with suppress(KeyboardInterrupt):
                self.client.loop.run_until_complete(binance_balance.bot_async.close())

            if cfg.discord_sent_msg:
                self.client.loop.run_until_complete(cfg.discord_sent_msg.delete())

            self.client.loop.close()
            log("## program is ended", is_write=False)
        except SystemExit:
            pass
        except Exception as e:
            print_tb(e)
            breakpoint()  # DEBUG

    async def task(self, tz="Europe/Istanbul"):
        """Add task in order to schedule discord to send messages.

        - runs every minute: 10th second (..., minute="*", second="10")
        - runs every 30 seconds (..., second="*/30")
        - runs at the 30th second (..., second="30")
        """
        await self.update_current_date()
        await helper.exchange.set_markets()
        await self.main()
        await self.record_balance()
        await self.fetch_balance()
        scheduler = AsyncIOScheduler()

        # secondly
        scheduler.add_job(self.main, "cron", second=f"*/{cfg.SLEEP_INTERVAL}", timezone=tz)
        if config.cfg["root"][cfg.TYPE]["status"] == "on":
            scheduler.add_job(self.fetch_balance, "cron", second="*/10", timezone=tz)

        # hourly
        scheduler.add_job(self.update_current_date, "cron", hour="*", timezone=tz)
        scheduler.add_job(self.record_balance, "cron", hour="*", timezone=tz)

        # daily
        scheduler.add_job(
            self.restart, "cron", year="*", month="*", day="*", hour="03", minute="01", second="0", timezone=tz
        )
        scheduler.start()

    async def pre_discord_setup(self):
        if not self.client.is_ready():
            await self.client.wait_until_ready()

        if not self.channel:
            self.channel = discord.utils.get(self.client.get_all_channels(), name=self.channel_name)

        if not self.channel_alerts:
            self.channel_alerts = discord.utils.get(self.client.get_all_channels(), name="alerts")

    async def fetch_balance(self):
        key = f"{cfg.TYPE}_timestamp"
        pos_count = 0
        del_list = []
        ongoing_positions = []
        try:
            cfg.BALANCES = await helper.exchange.spot.fetch_balance()
            for symbol in cfg.BALANCES:
                if (
                    symbol not in ["BTC", "BNB", "USDT", "info", "timestamp", "datetime", "free", "used", "total"]
                    and cfg.BALANCES[symbol]["total"] > 0
                ):
                    ongoing_positions.append(symbol)
                    if symbol not in cfg.STABLE_COINS and symbol not in config.SPOT_IGNORE_LIST:
                        pos_count += 1

            for asset_timestamp in config.timestamp[key]:
                if asset_timestamp != "base" and asset_timestamp not in ongoing_positions:
                    del_list.append(asset_timestamp)

            for asset in del_list:
                del config.timestamp[key][asset]

            config.env[cfg.TYPE]._status.add_single_key("count", pos_count)
        except Exception as e:
            log(f"E: {e}")

    async def update_current_date(self):
        cfg.CURRENT_DATE = _date(zone="UTC", _type="year")

    async def record_balance(self):
        config.env[cfg.TYPE].balance.add_single_key(
            cfg.CURRENT_DATE, {"btc": float(cfg.SUM_BTC), "usdt": float(cfg.SUM_USDT)}
        )

    async def restart(self):
        log()
        log("#> -=-=-=-=-=-=-=-=-=-=-=- RESTARTING -=-=-=-=-=-=-=-=-=-=-=- [blue]<#", is_write=False)
        os.execv(sys.argv[0], sys.argv)

    async def main(self):
        await self.pre_discord_setup()
        await process_main(self)


def main():
    try:
        _type = sys.argv[1:][0]
    except:
        _type = "usdt"

    Discord_Alpy(_type)


if __name__ == "__main__":
    main()
