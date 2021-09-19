#!/usr/bin/env python3

import asyncio
import logging

import quart.flask_patch  # noqa
from flask import abort, request  # noqa
from quart import Quart

from ebloc_broker.broker._utils.tools import QuietExit, _colorize_traceback, _exit, log

logging.getLogger("requests").setLevel(logging.CRITICAL)

app = Quart(__name__)
_server = None


async def start():
    # margin_usdt = app.client_helper.get_balance_margin_USDT()
    # if not is_process_on("[n]grok", "ngrok"):
    #     sys.exit(1)
    print(" * s t a r t i n g", flush=True)


async def do_trade(msg):
    """Trade based on the given arguments.

    asyncio.Lock() is required to protect following critical section trade
    orders may take action based on previously received alert's order. While one
    coroutine is inside app.bot_trade.trade_main(), making the `aiohttp` call,
    and another waits on app.lock. Any coroutine that calls into get_stuff will
    have to wait for the app.lock.

    __ https://stackoverflow.com/a/25799871/2402577
    """
    async with app.lock:
        await app.bot_trade.trade_main(msg)


@app.before_serving
async def startup():
    """Startup function.

    __ https://pgjones.gitlab.io/quart/how_to_guides/startup_shutdown.html
    """
    from bot.client_helper import ClientHelper, DiscordClient
    from bot import helper
    import bot.trade_async as bot_trade
    from user_setup import check_binance_obj

    loop = asyncio.get_event_loop()
    app.discord_client = DiscordClient()
    await app.discord_client.bot.login(app.discord_client.TOKEN)
    loop.create_task(app.discord_client.bot.connect())
    client, app.balances = check_binance_obj()
    app.client_helper = ClientHelper(client)
    await helper.exchange.set_markets()
    app.bot_trade = bot_trade.BotHelper(client, app.discord_client)
    app._bot_trade = bot_trade
    app.lock = asyncio.Lock()
    await start()


@app.route("/")
async def notify():  # noqa
    return "OK"


@app.route("/webhook", methods=["POST"])
async def webhook():
    """Receive webhook from tradingview."""
    if request.method != "POST":
        abort(400)

    data_msg = request.get_data(as_text=True)
    if data_msg:
        try:
            if any(n in data_msg for n in ["enter", "alert"]):
                await do_trade(data_msg.rstrip())

            return "OK"
        except QuietExit as e:
            if e:
                log(e)
        except KeyError:
            _exit("=============exception_catched=============")
        except Exception as e:
            _colorize_traceback(e)

        return "", 200
    else:
        abort(403)


def main():
    app.run("", port=5000, debug=False)


if __name__ == "__main__":
    main()
