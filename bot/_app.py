#!/usr/bin/env python3

import logging
import os
import sys  # noqa

from actions import parse_webhook
from broker._utils.tools import _colorize_traceback, _time, log
from broker.utils import is_process_on  # noqa
from dotenv import load_dotenv
from flask import Flask, abort, request
from gevent.pywsgi import WSGIServer
from trade import BotHelper, Strategy
from user_setup import check_binance_obj

from bot.client_helper import ClientHelper

load_dotenv()

logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL),
logging.getLogger("gunicorn").setLevel(logging.CRITICAL),

app = Flask(__name__)
app.debug = False

client, balances = check_binance_obj()
bot = BotHelper(client)
FUND_TIMES = [19, 3, 11]
is_trade = True
data_msg_temp = None
BTC_MAX_POSITION_NUMBER = int(os.getenv("BTC_MAX_POSITION_NUMBER"))
USDT_MAX_POSITION_NUMBER = int(os.getenv("USDT_MAX_POSITION_NUMBER"))


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free"]
        break


def check_on_going_positions(strategy) -> bool:
    if strategy.market == "USDTPERP":
        usdt_open_position_size = bot.get_usdt_open_position_count()
        if usdt_open_position_size >= USDT_MAX_POSITION_NUMBER:
            # log(f"Warning: There is already ongoing {USDT_MAX_POSITION_NUMBER} of positions, nothing to do.")
            return True
    elif strategy.market == "BTC":
        btc_open_position_size = bot.get_btc_open_positions()
        if btc_open_position_size >= BTC_MAX_POSITION_NUMBER:
            # log(f"Warning: There is already ongoing {BTC_MAX_POSITION_NUMBER} of positions, nothing to do.")
            return True
    return False


def _trade(strategy):
    if strategy.market_position == "flat":
        live_pos_side = bot.get_open_position_side(strategy.symbol)
        log(f"==> live_pos_side={live_pos_side}")
        if strategy.prev_market_position == live_pos_side:
            bot.strategy_exit(strategy)
    else:
        is_open = False
        if strategy.market == "USDTPERP":
            is_open = bot.is_usdt_open_open(strategy.symbol)
        elif strategy.market == "BTC":
            balances = bot.client.get_account()
            for balance in balances["balances"]:
                if balance["asset"] == strategy.asset and float(balance["locked"]) > 0.0:
                    is_open = True
                    break

        if not is_open:
            try:
                bot.strategy = strategy
                bot.trade()
                log("SUCCESS")
            except Exception as e:
                _colorize_traceback(e)


def trade_func(data_msg):
    global data_msg_temp
    is_print = True
    if "enter" in data_msg:
        _data_msg = data_msg.split(", (", 1)[0].split(",")[0]
        if data_msg_temp != _data_msg:
            data_msg_temp = _data_msg
        else:  # prevents same alert messages to print
            is_print = False

    strategy = Strategy(data_msg, is_print)
    if "enter" in data_msg and is_print:
        future_positions = bot.exchange_future.fetch_positions()
        for position in future_positions:
            if abs(float(position["info"]["positionInitialMargin"])) > 0.0:
                log(f" {position['symbol'].replace('/USDT', '')} ", end="", color="cyan")

        if len(future_positions) > 0:
            log("")

    try:
        strategy.position_alert_msg
    except:
        return True

    if "enter" not in strategy.position_alert_msg or strategy.symbol == "TEST" or check_on_going_positions(strategy):
        # log("Warning: ignore, nothing to do")
        pass
    elif strategy.market == "BTC" and strategy.is_sell():
        log("Warning: Ignore BTC pair, no need to sell")
    elif is_trade:
        _trade(strategy)

    return True


@app.route("/")
def root():
    text = f"==>  {_time()}"
    log(text, color="green")
    return text


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            try:
                trade_func(data_msg)
            except Exception as e:
                _colorize_traceback(e)
                log("EXCEPTION catched", color="red")
                # TODO: trade_func(data_msg)

            return "", 200
        else:
            log("E: abort")
            abort(403)
    else:
        log("E: abort")
        abort(400)


if __name__ == "__main__":
    client_helper = ClientHelper(client)
    margin_usdt = client_helper.get_balance_margin_USDT()
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
    future_positions = bot.exchange_future.fetch_positions()
    log(f" * Futures {futures_usd} USD | SPOT={client_helper._format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    usdt_open_position_size = bot.get_usdt_open_position_count()
    log(f"   * usdt_open_position_size={usdt_open_position_size}")
    log(" * =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="blue")
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
