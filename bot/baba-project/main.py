#!/usr/bin/env python3

import asyncio
import time
from pathlib import Path

import discord
from broker._utils._log import log
from broker._utils.yaml import Yaml
from tradingview_ta import Interval, TA_Handler

cfg = Yaml(Path(f"{Path.home()}/.binance.yaml"))
client = discord.Client()
channel_name = "bist"
TOKEN = str(cfg["discord"]["TOKEN"])

client = discord.Client()
flag = {}
ta_handler = {}


async def work(channel):
    for key, value in ta_handler.items():
        osc = value.get_analysis().oscillators
        log(osc)
        if flag[key]:
            if osc["COMPUTE"]["Mom"] == "BUY" and osc["COMPUTE"]["MACD"] == "BUY":
                flag[key] = False
                await channel.send(f"{key} BUY")
                # breakpoint()  # DEBUG

        if not flag[key]:
            if osc["COMPUTE"]["Mom"] == "SELL" or osc["COMPUTE"]["MACD"] == "SELL":
                flag[key] = True
                await channel.send(f"{key} SELL")

    time.sleep(15)


async def my_background_task():
    # https://stackoverflow.com/questions/49835742/how-to-send-a-message-with-discord-py-without-a-command
    # https://github.com/brian-the-dev/python-tradingview-ta
    # https://tvdb.brianthe.dev
    # for symbol in ["ENKAI", "XU100"]:
    for symbol in ["ENKAI"]:
        ta_handler[symbol] = TA_Handler(
            symbol=symbol,
            screener="turkey",
            exchange="BIST",
            interval=Interval.INTERVAL_5_MINUTES,
            # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
        )

    for key, value in ta_handler.items():
        flag[key] = True

    print("staring...")

    await client.wait_until_ready()
    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    await channel.send("starting...")
    while not client.is_closed():
        try:
            await work(channel)
        except Exception as e:
            log(f"E: {e}")

        await asyncio.sleep(20)  # task runs every 60 seconds


@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")


client.loop.create_task(my_background_task())
client.run(TOKEN)


# async def main():


# if __name__ == "__main__":
#     asyncio.get_event_loop().run_until_complete(main())
