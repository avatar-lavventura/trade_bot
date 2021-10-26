#!/usr/bin/env python3

from pathlib import Path

from _mongodb import Mongo
from pymongo import MongoClient
from tools import print_tb
from user_setup import check_binance_obj

HOME = str(Path.home())
initial_btc_quantity = 0.0002
INITIAL_USDT_QTY = 15
DCA = [5, 10, 25]
TP = 0.0052
TAKE_PROFIT_LONG = 1.000 + TP


if __name__ == "__main__":  # noqa: C901
    mc = MongoClient()
    db = Mongo(mc, mc["trader_bot"]["order"])
    client, _ = check_binance_obj()
    asset = "EOS"
    _symbol = "EOSBTC"
    contracts = 0.0
    _sum = 0.0
    try:
        output = db.find_key("symbol", _symbol)
        timestamp = output["timestamp"]
        print(f"timestamp={timestamp}")
        asset_balance = 0
        balances = client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] == asset:
                asset_balance = float(balance["free"]) + float(balance["locked"])
                break

        quantity = 0
        for idx, trade in enumerate(reversed(client.get_my_trades(symbol=_symbol))):
            if idx == 0:
                decimal_count = len(str(trade["price"]).split(".")[1])

            if trade["isBuyer"] and trade["time"] >= timestamp:
                quantity += float(trade["qty"])
                if quantity > asset_balance:
                    break

                print(trade)
                _sum += float(trade["qty"]) * float(trade["price"])
                contracts += float(trade["qty"])

        entry_price = _sum / contracts
        _price = f"{entry_price:.{decimal_count}f}"
        print(f"entry_price={_price}")
        limit_price = f"{float(_price) * TAKE_PROFIT_LONG:.{decimal_count}f}"
        print(f"limit_price={limit_price}")
    except Exception as e:
        print_tb(e)

    # balances = client.get_account()
    # for balance in balances["balances"]:
    #     if balance["asset"] != "BNB" and float(balance["free"]) + float(balance["locked"]) > 0.00000000:
    #         print(balance)
