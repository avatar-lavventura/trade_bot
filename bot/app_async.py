#!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path

import quart.flask_patch  # noqa
from broker._utils._log import log
from broker._utils.tools import _date, print_tb
from broker.errors import QuietExit
from flask import abort, request
from quart import Quart

from bot.config import config

logging.disable(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)


app = Quart(__name__)
liner = "======================"


async def do_alert(msg):
    async with app.alertlock:
        await app.bot_trade.alert_main(msg)


async def trade(msg):
    """Trade based on the given arguments.

    asyncio.Lock() is required to protect following critical section trade
    orders may take action based on previously received alert's order.  While
    one coroutine is inside app.bot_trade.trade_main(), making the `aiohttp`
    call, and another waits on app.lock. Any coroutine that calls into
    get_stuff will have to wait for the app.lock.

    __ https://stackoverflow.com/a/25799871/2402577
    """
    async with app.lock:
        await app.bot_trade.trade_main(msg)


@app.before_serving
async def startup():
    """Launch right before serving the quart server.

    __ https://pgjones.gitlab.io/quart/how_to_guides/startup_shutdown.html
    """
    from broker._utils import _log

    import bot.trade_async as bot_trade
    from bot import config as helper
    from bot.client_helper import DiscordClient

    _log.ll.LOG_FILENAME = Path.home() / ".bot" / "program.log"
    loop = asyncio.get_event_loop()
    app.discord_client = DiscordClient()
    await app.discord_client.bot.login(app.discord_client.TOKEN)
    loop.create_task(app.discord_client.bot.connect())
    helper.exchange.init_both()
    await helper.exchange.set_markets()
    app.bot_trade = bot_trade.BotHelper(app.discord_client)
    app._bot_trade = bot_trade
    app.alertlock = asyncio.Lock()
    app.lock = asyncio.Lock()
    if not config.cfg["root"]["is_write"]:
        _log.IS_WRITE = False

    print("* s t a r t i n g . . .")


@app.after_serving
async def _finally():
    for key in config.btc_wavetrend:
        config.btc_wavetrend[key] = "none"


@app.route("/")
async def notify():
    return "OK"


@app.route("/webhook", methods=["POST"])
async def webhook() -> (str, int):
    """Receive webhook message from the tradingview-alerts."""
    if request.method != "POST":
        abort(400)

    data_msg = request.get_data(as_text=True)
    if data_msg:
        if data_msg in ["red", "green"]:  # "alert_wavetrend"
            await do_alert(data_msg)
            text = ""
            if data_msg.upper() == "RED":
                text = f"  [red]{data_msg.upper()}[/red]  "
            elif data_msg.upper() == "GREEN":
                text = f"  [green]{data_msg.upper()}[/green]  "

            log(
                f" {liner}  [y]wt_30m[/y]=[{text}]   {_date(_type='hour')}  {liner}",
                end="\r",
                is_write=False,
                highlight=False,
            )
        else:
            for asset in ["BTC", "USDT", "BUSD"]:
                if asset in data_msg and config.cfg["root"][asset.lower()]["status"] == "off":
                    return "OK", 0

            try:
                if any(x in data_msg for x in ["enter", "alert"]):
                    await trade(data_msg.replace(":00Z", "").rstrip())

                return "OK", 0
            except (QuietExit, KeyError) as e:
                if e:
                    log(str(e), "bold")
            except Exception as e:
                print_tb(e)
        return "", 200
    else:
        abort(403)


def main():
    app.run("", port=5000, debug=False)


if __name__ == "__main__":
    main()
