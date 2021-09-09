#!/usr/bin/env python3

import logging
from pathlib import Path

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ebloc_broker.broker._utils.tools import get_dt_time
from ebloc_broker.broker._utils.yaml import Yaml

logging.getLogger("apscheduler.executors.default").propagate = False


class Discord_Alpy:
    def __init__(self):
        _config = Yaml(Path(f"{Path.home()}/.binance.yaml"))
        self.client = discord.Client()
        self.TOKEN = _config["discord"]["TOKEN"]
        self.channel_id = _config["discord"]["CHANNEL_ALPY"]
        try:
            self.client.loop.create_task(self.task())
            self.client.loop.run_until_complete(self.client.start(self.TOKEN))
        except SystemExit:
            pass
        except KeyboardInterrupt:
            self.client.loop.close()
            print("Program ended.")

    async def task(self):
        """Add task.

        - every minute, 10th second: (..., minute="*", second="10")
        - every 30 seconds: (..., second="*/30")
        - at 30th second: (..., second="30")
        """
        scheduler = AsyncIOScheduler()
        # scheduler.add_job(self.send_msg, "cron", hour="12")
        # scheduler.add_job(self.send_msg, "cron", hour="18")
        # For test purposes
        scheduler.add_job(self.send_msg, "cron", second="*/30", timezone="Europe/Istanbul")
        scheduler.start()

    async def send_msg(self, msg=""):
        await self.client.wait_until_ready()
        channel = self.client.get_channel(self.channel_id)
        if not msg:
            msg = f"Tick! The time is: {get_dt_time().strftime('%Y-%m-%d %H:%M:%S')}"
            print(msg)
            await channel.send(msg)
        # await binance_balance.process_main(channel)


_discord = Discord_Alpy()

# global MESSAGE
# await self.client.wait_until_ready()
# while True:
#     current_time = self.tick()
#     channel = self.client.get_channel(self.channel_id)
#     if MESSAGE:
#         await MESSAGE.delete()

#     MESSAGE = await channel.send(current_time)
#     # this also works
#     # await message.channel.send('Goodbye in 3 seconds...', delete_after=3.0)
#     await asyncio.sleep(10)

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     if message.content.startswith('$hello'):
#         await message.channel.send('Hello!')
# async def _send_msg(msg):
#     await _discord.client.wait_until_ready()
#     channel = _discord.client.get_channel(_discord.channel_id)
#     await channel.send(msg)
