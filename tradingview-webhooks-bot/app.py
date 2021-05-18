#!/usr/bin/env python3

import datetime

from actions import parse_webhook
from buy import BotHelper, trade, Strategy
from flask import Flask, abort, request
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
# TODO: before 15 close all positions if in gain


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free"]
        break


def _format(value, decimal=2):
    return format(float(value), ".2f")


class ClientHelper:
    def __init__(self, client):
        self.client = client

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
            print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
            print(f" * Current date and time: {now}")
            strategy = Strategy(data_msg)

            if strategy.symbol == "TEST":
                print("==> TEST message successfully received")
            elif is_trade:
                if strategy.market_position == "flat":
                    bot.strategy_exit(strategy)
                else:
                    print(f"==> LATEST_POSITION={LATEST_POSITION}")

                    if LATEST_POSITION != strategy.side:  # if the position reversed
                        trade(client, strategy)
                        LATEST_POSITION = strategy.side
                    else:
                        print("==> Did not entered trading")
            print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
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

    print(f" * Futures={futures_usd} USD | SPOT={_format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    print(f" * is_trade={is_trade}")
    now = datetime.datetime.now()
    print(f" * Current date and time: {now}")
    print(" * -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
    # app.debug = True
    app.run()
    # app.run(host="0.0.0.0", port="33")
    # app.run(host="34.89.13.197", port="5000")
    # 1640463783:AAGZ3k1ox9--LnjfVPdsXX2xvAxn-VFXmeo
