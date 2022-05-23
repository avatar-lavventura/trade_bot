#!/usr/bin/env python3

import logging
import sys
from contextlib import suppress
from pathlib import Path
from bot.config import config
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from broker._utils import _log
from broker._utils.tools import _date, print_tb
from broker._utils.yaml import Yaml

from bot import binance_balance, cfg, helper
from bot.binance_balance import process_main

logging.disable(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("apscheduler.executors.default").propagate = False


class Discord_Alpy:
    def __init__(self, _type):
        try:
            self._type = cfg.TYPE = _type.lower()
            _log.ll.LOG_FILENAME = Path.home() / ".bot" / f"program_{_type}.log"
            print(f" * bot_type={_type}")
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
            print("## program is ended")
        except SystemExit:
            pass
        except Exception as e:
            print_tb(e)
            breakpoint()  # DEBUG

    async def task(self):
        """Add task in order to schedule discord to send messages.

        - runs every minute, 10th second: (..., minute="*", second="10")
        - runs every 30 seconds: (..., second="*/30")
        - runs at 30th second: (..., second="30")
        """
        cfg.CURRENT_DATE = _date(_type="month")
        await helper.exchange.set_markets()
        await self.main()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.main, "cron", second=f"*/{cfg.SLEEP_INTERVAL}", timezone="Europe/Istanbul")
        scheduler.add_job(self._fetch_balance, "cron", second="*/5", timezone="Europe/Istanbul")
        scheduler.add_job(self.update_current_date, "cron", hour="*", timezone="Europe/Istanbul")
        scheduler.start()

    async def pre_discord_setup(self):
        if not self.client.is_ready():
            await self.client.wait_until_ready()

        if not self.channel:
            self.channel = discord.utils.get(self.client.get_all_channels(), name=self.channel_name)

        if not self.channel_alerts:
            self.channel_alerts = discord.utils.get(self.client.get_all_channels(), name="alerts")

    async def _fetch_balance(self):
        try:
            ongoing_positions = []
            cfg.BALANCES = await helper.exchange.spot.fetch_balance()
            for symbol in cfg.BALANCES:
                if symbol not in ["info", "BTC", "BNB", "USDT", "timestamp", "datetime", "free", "used", "total"]:
                    if cfg.BALANCES[symbol]["total"] > 0.0:
                        ongoing_positions.append(symbol)

            del_list = []
            key = f"{cfg.TYPE}_timestamp"
            for asset_timestamp in config.timestamp[key]:
                if asset_timestamp != "base" and asset_timestamp not in ongoing_positions:
                    del_list.append(asset_timestamp)

            for asset in del_list:
                if asset not in config.SPOT_IGNORE_LIST:
                    del config.timestamp[key][asset]
                    print(f"#> TIMESTAMP DELETED for {asset}")
        except Exception as e:
            print(f"E: {e}")

    async def update_current_date(self):
        cfg.CURRENT_DATE = _date(_type="month")

    async def main(self):
        await self.pre_discord_setup()
        await process_main(self)


if __name__ == "__main__":
    try:
        _type = sys.argv[1:][0]
    except:
        _type = "usdt"

    Discord_Alpy(_type)
