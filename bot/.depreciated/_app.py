#!/usr/bin/env python3

import asyncio
import sys  # noqa
import time
from contextlib import suppress

from actions import parse_webhook
from broker._utils.tools import _time, log, print_tb
from broker.utils import is_process_on  # noqa
from dotenv import load_dotenv
from flask import Flask, abort, request
from gevent.pywsgi import WSGIServer
from trade import BotHelper
from user_setup import check_binance_obj

from bot.client_helper import ClientHelper

load_dotenv()

loop = asyncio.get_event_loop()
app = Flask(__name__)
app.debug = True

client, balances = check_binance_obj()
bot = BotHelper(client)


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free_usdt"]
        break


@app.route("/")
def root():
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            try:
                bot.trade_main(data_msg)
                return "OK"
            except Exception as e:
                print_tb(e)
                log("EXCEPTION catched", color="red")
                time.sleep(15)

            return "", 200
        else:
            log("E: abort")
            abort(403)
    else:
        log("E: abort")
        abort(400)


async def close():
    """Close async program.

    https://stackoverflow.com/a/54528397/2402577
    """
    log("Finalizing...")
    await asyncio.sleep(0.1)


async def main():
    client_helper = ClientHelper(client)
    margin_usdt = client_helper.get_balance_margin_usdt()
    filename = ".ip"
    with open(filename) as f:
        _ip = f.readlines()

    # if not is_process_on("[n]grok", "ngrok"):
    #     sys.exit(1)

    print(" * s t a r t i n g", flush=True)
    log(f" * {_ip[0].rstrip()}")
    futures_usd = client_helper._get_futures_usdt()
    log(f" * Current date and time: {_time()}")
    bot.get_btc_open_positions()
    client_helper.spot_balance()
    log(f" * Futures {futures_usd} USD | SPOT={client_helper._format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    usdt_open_position_size = bot.get_futures_open_position_count()
    log(f"   * usdt_open_position_size={usdt_open_position_size}")
    log(" * =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="blue")
    app_server = WSGIServer(("0.0.0.0", 5000), app)
    app_server.serve_forever()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        with suppress(Exception):
            loop.run_until_complete(close())
    except Exception as e:
        print_tb(e)
    finally:
        log("Program finished.", color="green")
