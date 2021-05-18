#!/usr/bin/env python3

import datetime

from actions import parse_webhook
from buy import trade, strategy_exit
from flask import Flask, abort, request
from user_setup import check_binance_obj

from binance_lib import get_futures_usd
from utils import log

# Create Flask object called app.
app = Flask(__name__)
client, balances = check_binance_obj()
ASSET_NAME = "DOGEUSDT"
LATEST_POSITION = None
IS_EVERY_MINUTE = False
is_trade = True
fund_times = [19, 3, 11]
# TODO: before 15 close all positions if in gain


for balance in balances["balances"]:
    if balance["asset"] == "USDT":
        usdt_balance = balance["free"]
        break


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
            print(f" * Current date and time: {now}")
            print(data_msg)
            chunks = data_msg.split(",")
            output = chunks[0]
            side = chunks[1]
            _type = chunks[2]

            print(f" * LATEST_POSITION={LATEST_POSITION}")
            if output == "TEST":
                print("==> TEST message successfully received")
            elif _type == "MIN" and not IS_EVERY_MINUTE:
                pass
            elif _type == "CLOSE_POS":
                strategy_exit(output, side)
            else:
                if LATEST_POSITION != side:  # if the position reversed
                    if is_trade:
                        trade(client, data_msg)

                    LATEST_POSITION = side
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
    print(f" * ASSET_NAME={ASSET_NAME}")
    print(f" * Futures={futures_usd} USD | SPOT={_format(usdt_balance)} USD | MARGIN={margin_usdt} ")
    print(f" * is_trade={is_trade}")
    now = datetime.datetime.now()
    print(f" * Current date and time: {now}")
    log(" * -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
    app.run()  # app.debug = True
