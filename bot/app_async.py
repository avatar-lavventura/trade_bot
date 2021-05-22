#!/usr/bin/env python3


import asyncio
import time
import quart.flask_patch  # noqa
from actions import parse_webhook
from broker._utils.tools import _colorize_traceback, log, _time
from flask import abort, request
from quart import Quart

loop = asyncio.get_event_loop()
app = Quart(__name__)
# app.debug = True


async def start():
    from bot.client_helper import ClientHelper
    from user_setup import check_binance_obj
    import bot.trade as bot_trade

    client, balances = check_binance_obj()
    client_helper = ClientHelper(client)
    margin_usdt = client_helper.get_balance_margin_USDT()
    filename = ".ip"
    with open(filename) as f:
        _ip = f.readlines()

    # if not is_process_on("[n]grok", "ngrok"):
    #     sys.exit(1)

    for balance in balances["balances"]:
        if balance["asset"] == "USDT":
            usdt_balance = balance["free"]
            break

    print(" * s t a r t i n g", flush=True)
    log(f" * {_ip[0].rstrip()}")
    futures_usd = client_helper._get_futures_usdt()
    log(f" * Current date and time: {_time()}")
    bot_trade.bot.get_btc_open_positions()
    client_helper.spot_balance()
    log(f" * Futures {futures_usd} USD | SPOT={client_helper._format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    usdt_open_position_size = await bot_trade. bot.get_usdt_open_position_count()
    log(f"   * usdt_open_position_size={usdt_open_position_size}")
    log(" * =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="blue")


@app.before_serving
async def startup():
    import bot.helper as helper
    import bot.trade as bot_trade
    app.exchange = helper.exchange
    app.bot_trade = bot_trade
    await start()


@app.route("/")
async def notify():
    print("OK")
    return "OK"


@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == "POST":
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            try:
                await app.bot_trade.bot.trade_main(data_msg)
                return "OK"
            except Exception as e:
                _colorize_traceback(e)
                log("EXCEPTION catched", color="red")
                time.sleep(15)

            return "", 200
        else:
            log("E: abort")
            abort(403)
    else:
        log("E: abort")
        abort(400)


if __name__ == "__main__":
    app.run("", port=5000, debug=False)
