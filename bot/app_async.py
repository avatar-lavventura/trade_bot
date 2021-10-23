#!/usr/bin/env python3

import asyncio
import logging
import quart.flask_patch  # noqa
from flask import abort, request  # noqa
from quart import Quart
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import QuietExit, _exit, print_tb

logging.getLogger("requests").setLevel(logging.CRITICAL)

app = Quart(__name__)


async def start():
    # margin_usdt = app.client_helper.get_balance_margin_usdt()
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
    from bot.user_setup import check_binance_obj
    import bot.trade_async as bot_trade

    loop = asyncio.get_event_loop()
    app.discord_client = DiscordClient()
    await app.discord_client.bot.login(app.discord_client.TOKEN)
    loop.create_task(app.discord_client.bot.connect())
    client, app.balances = check_binance_obj()  # TODO
    app.client_helper = ClientHelper(client)
    await helper.exchange.set_markets()
    app.bot_trade = bot_trade.BotHelper(client, app.discord_client)
    app._bot_trade = bot_trade
    app.lock = asyncio.Lock()
    await start()


@app.route("/")
async def notify():
    return "OK"


@app.route("/webhook", methods=["POST"])
async def webhook():
    """Receive webhook from tradingview."""
    if request.method != "POST":
        abort(400)

    data_msg = request.get_data(as_text=True)
    if data_msg:
        try:
            if any(x in data_msg for x in ["enter", "alert"]):
                await do_trade(data_msg.replace(":00Z", "").rstrip())

            return "OK"
        except QuietExit as e:
            if e:
                log(str(e), "bold")
        except KeyError:
            _exit("E: KeyError")
        except Exception as e:
            print_tb(e)

        return "", 200
    else:
        abort(403)


def main():
    app.run("", port=5000, debug=False)


if __name__ == "__main__":
    main()
