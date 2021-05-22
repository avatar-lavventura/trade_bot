#!/usr/bin/env python3

from datetime import datetime

from actions import parse_webhook
from buy import BotHelper, Strategy, trade
from flask import Flask, abort, request
from gevent.pywsgi import WSGIServer
from pytz import timezone
from tools import log
from user_setup import check_binance_obj

from binance_lib import get_futures_usd

# Create Flask object called app.
app = Flask(__name__)
client, balances = check_binance_obj()
fund_times = [19, 3, 11]
LATEST_POSITION = None
IS_EVERY_MINUTE = False
is_trade = True
bot = BotHelper(client)
MAX_POSITION_NUMBER = 2


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free"]
        break


def _time():
    format = "%Y-%m-%d %H:%M:%S"
    country_time = datetime.now(timezone("Europe/Istanbul"))
    return country_time.strftime(format)


class ClientHelper:
    def __init__(self, client):
        self.client = client

    def _format(self, value, decimal=2):
        return format(float(value), ".2f")

    def transfer_futures_to_spot(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="2")

    def transfer_spot_to_futures(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="1")

    def transfer_spot_to_margin(self, amount):
        self.client.transfer_spot_to_margin(asset="USDT", amount=float(amount), type="1")

    def get_balance_margin_USDT(self):
        try:
            _len = len(self.client.get_margin_account()["userAssets"])
            for x in range(_len):
                if self.client.get_margin_account()["userAssets"][x]["asset"] == "USDT":
                    balance_USDT = self.lient.get_margin_account()["userAssets"][x]["free"]
                    return float(balance_USDT)
        except:
            pass

        return 0


# Create root to easily let us know its on/working.
@app.route("/")
def root():
    return "online"


@app.route("/webhook", methods=["POST"])
def webhook():
    global LATEST_POSITION
    if request.method == "POST":
        # Parse the string data from tradingview into a python dict
        data_msg = parse_webhook(request.get_data(as_text=True))
        if data_msg:
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            log(f" * Current date and time: {_time()}")
            strategy = Strategy(data_msg)
            open_position_size = bot.open_positions()
            log(f"open_position_size={open_position_size}")
            breakpoint()  # DEBUG
            if open_position_size > MAX_POSITION_NUMBER:
                log(f"Warning: There is already ongoing {MAX_POSITION_NUMBER} positions, nothing to do.")
            elif strategy.symbol == "TEST":
                log("==> TEST message successfully received")
            elif is_trade:
                log(f"==> LATEST_POSITION={LATEST_POSITION}")
                if strategy.market_position == "flat":
                    # DOGEUSDTPERP,sell,flat,long
                    # 11:36:02  11:36:01 may come 2 millisecond differ
                    live_pos_side = bot.get_open_position_side(strategy.symbol)
                    log(f"==> live_pos_side={live_pos_side}")
                    # if not LATEST_POSITION or strategy.prev_market_position == LATEST_POSITION:
                    if strategy.prev_market_position == live_pos_side:
                        bot.strategy_exit(strategy)
                        LATEST_POSITION = strategy.market_position
                        log(f"==> UPDATED_LATEST_POSITION={LATEST_POSITION}")
                else:
                    if strategy.prev_market_position != strategy.market_position:
                        try:
                            trade(client, strategy)
                            log(
                                "SUCCESS in trade", color="green"
                            )  # if not try again in 15 seconds in case binance frozes
                        except Exception as e:
                            log(str(e), color="red")
                            pass

                        LATEST_POSITION = strategy.market_position
                        log(f"==> UPDATED_LATEST_POSITION={LATEST_POSITION}")
                    else:
                        log("## Didn't do any trading")
                        log(f"==> LATEST_POSITION={LATEST_POSITION}")
                        log(f"==> prev_market_position={strategy.prev_market_position}")
                        log(f"==> strategy_side={strategy.side}")

            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            return "", 200
        else:
            abort(403)
    else:
        abort(400)


if __name__ == "__main__":
    client_helper = ClientHelper(client)
    futures_usd = get_futures_usd(client, is_both=False)
    margin_usdt = client_helper.get_balance_margin_USDT()
    total_balance = float(futures_usd) + float(usdt_balance) + margin_usdt

    filename = "ngrok_ip"
    with open(filename) as f:
        ngrok_ip = f.readlines()

    print(" * s t a r t i n g", flush=True)
    log(f" * {ngrok_ip[0].rstrip()}")
    log(f" * is_trade={is_trade}")
    log(f" * Futures={futures_usd} USD | SPOT={client_helper._format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    log(f" * Current date and time: {_time()}")
    bot.open_positions()
    log(" * -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
