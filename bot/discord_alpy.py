#!/usr/bin/env python3

import asyncio
import os
from datetime import datetime

import discord
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()

client = discord.Client()

TOKEN = os.getenv("TOKEN")
channel_id = int(os.getenv("CHANNEL"))


async def _time(zone="Europe/Istanbul"):
    _format = "%Y-%m-%d %H:%M:%S"
    country_time = datetime.now(timezone(zone))
    return country_time.strftime(_format)


async def task():
    await client.wait_until_ready()
    while True:
        current_time = await _time()
        channel = client.get_channel(channel_id)
        await channel.send(current_time)
        await asyncio.sleep(10)


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))
    print(client.user.name)
    print(client.user.id)
    print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")


# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     if message.content.startswith('$hello'):
#         await message.channel.send('Hello!')

try:
    client.loop.create_task(task())
    client.loop.run_until_complete(client.start(TOKEN))
except SystemExit:
    pass
    # handle_exit()
except KeyboardInterrupt:
    # handle_exit()
    client.loop.close()
    print("Program ended.")
