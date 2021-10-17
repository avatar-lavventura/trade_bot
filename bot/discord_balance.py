#!/usr/bin/env python3

import logging
from contextlib import suppress
from pathlib import Path

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot import binance_balance, helper
from bot.binance_balance import process_main
from ebloc_broker.broker._utils.tools import get_dt_time
from ebloc_broker.broker._utils.yaml import Yaml

logging.getLogger("apscheduler.executors.default").propagate = False


class Discord_Alpy:
    def __init__(self):
        try:
            _config = Yaml(Path.home() / ".binance.yaml")
            self.channel: str = ""
            self.client = discord.Client()
            self.channel_name = str(_config["discord"]["CHANNEL_NAME"])
            self.TOKEN = str(_config["discord"]["TOKEN"])
            self.client.loop.create_task(self.task())
            self.client.loop.run_until_complete(self.client.start(self.TOKEN))
        except SystemExit:
            pass
        except KeyboardInterrupt:
            with suppress(KeyboardInterrupt):
                self.client.loop.run_until_complete(binance_balance.bot_async.close())

            self.client.loop.close()
            print("Program ended.")

    async def task(self):
        """Add task in order to schedule discord to send messages.

        - every minute, 10th second: (..., minute="*", second="10")
        - every 30 seconds: (..., second="*/30")
        - at 30th second: (..., second="30")
        """
        await helper.exchange.set_markets()

        scheduler = AsyncIOScheduler()
        # scheduler.add_job(self.send_msg, "cron", hour="12")
        # scheduler.add_job(self.send_msg, "cron", hour="18")
        # For test purposes
        scheduler.add_job(self._process_main, "cron", second="*/20", timezone="Europe/Istanbul")
        scheduler.start()

    async def pre_discord_setup(self):
        if not self.client.is_ready():
            await self.client.wait_until_ready()

        if not self.channel:
            self.channel = discord.utils.get(self.client.get_all_channels(), name=self.channel_name)

    async def _process_main(self):
        await self.pre_discord_setup()
        await process_main(self.channel)

    async def send_msg(self, msg=""):
        await self.pre_discord_setup()
        if not self.channel:
            print("E: channel is empty")
        else:
            if not msg:
                msg = f"Tick! The time is: {get_dt_time().strftime('%Y-%m-%d %H:%M:%S')}"
                print(msg)
                await self.channel.send(msg)
        # await binance_balance.process_main(channel)


_discord = Discord_Alpy()
