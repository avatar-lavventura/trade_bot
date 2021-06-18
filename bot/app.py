#!/usr/bin/env python3

from actions import parse_webhook
from broker._utils.tools import _time, log
from flask import Flask, abort, request
from gevent.pywsgi import WSGIServer
from trade import BotHelper, Strategy
from user_setup import check_binance_obj

from bot.client_helper import ClientHelper

# Create Flask object called app.
app = Flask(__name__)
client, balances = check_binance_obj()
bot = BotHelper(client)
fund_times = [19, 3, 11]
is_trade = True
BTC_MAX_POSITION_NUMBER = 2
USDT_MAX_POSITION_NUMBER = 3


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free"]
        break


def check_on_going_positions(strategy) -> bool:
    if strategy.market == "USDT":
        _, usdt_open_position_size = bot.get_usdt_open_positions()
        if usdt_open_position_size >= USDT_MAX_POSITION_NUMBER:
            log(f"Warning: There is already ongoing {USDT_MAX_POSITION_NUMBER} of positions, nothing to do.")
            return True
    elif strategy.market == "BTC":
        btc_open_position_size = bot.get_btc_open_positions()
        if btc_open_position_size >= BTC_MAX_POSITION_NUMBER:
            log(f"Warning: There is already ongoing {BTC_MAX_POSITION_NUMBER} of positions, nothing to do.")
            return True
    return False


def trade_func(data_msg):
    log(f" * {_time()} ", end="")
    strategy = Strategy(data_msg)

    try:
        strategy.position_alert_msg
    except:
        return True

    if "enter" not in strategy.position_alert_msg or strategy.symbol == "TEST":
        log("Warning: ignore, nothing to do")
    elif check_on_going_positions(strategy):
        pass
    elif strategy.market == "BTC" and strategy.is_sell():
        log("==> Ignore BTC pair, no need to sell")
    elif is_trade:
        if strategy.market_position == "flat":
            live_pos_side = bot.get_open_position_side(strategy.symbol)
            log(f"==> live_pos_side={live_pos_side}")
            if strategy.prev_market_position == live_pos_side:
                bot.strategy_exit(strategy)
        else:
            is_open = False
            if strategy.market == "USDT":
                is_open, pos_size = bot.get_usdt_open_positions(strategy.symbol)
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
                    # TODO: if not try again in 15 seconds in case binance frozes
                except Exception as e:
                    log(str(e), color="red")
            else:
                log("## Pass, ongoing position exist")
    return True


# Create root to easily let us know its on/working.
@app.route("/")
def root():
    return "online"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        # Parse the string data from tradingview into a python dict
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            trade_func(data_msg)
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            return "", 200
        else:
            abort(403)
    else:
        abort(400)


if __name__ == "__main__":
    client_helper = ClientHelper(client)
    margin_usdt = client_helper.get_balance_margin_USDT()
    filename = "ngrok_ip"
    with open(filename) as f:
        ngrok_ip = f.readlines()

    print(" * s t a r t i n g", flush=True)
    log(f" * {ngrok_ip[0].rstrip()}")
    futures_usd = client_helper._get_futures_usdt()
    log(f" * Current date and time: {_time()}")
    _, pos_size = bot.get_usdt_open_positions()
    bot.get_btc_open_positions()
    client_helper.spot_balance()
    log(f" * Futures {futures_usd} USD | SPOT={client_helper._format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    log(" * =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="blue")
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
