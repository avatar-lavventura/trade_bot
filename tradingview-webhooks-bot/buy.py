#!/usr/bin/env python3

# altay: 1000 lot 4 kaldırac: toplam 4000 lot
# TODO: hard stop loss koy 10% zarara sonra kaldiraci arttirabilirsin
# TODO: min signal iterative 2 times check

import time
from pathlib import Path
from user_setup import check_binance_obj
from utils import log

HOME = str(Path.home())
AMOUNT = 700


def buy(symbol, amount, client):
    amount = abs(float(amount))
    print(f"amount={amount}")
    try:
        order = client.futures_create_order(symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=False)
    except:
        order = client.futures_create_order(symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=True)

    print(f"{order}\n")


def sell(symbol, amount, client):
    amount = abs(float(amount))
    print(f"amount={amount}")
    try:
        order = client.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=amount)
    except:
        order = client.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=amount, reduceOnly=True)

    print(f"{order}\n")


def strategy_exit(symbol, side):
    futures = client.futures_position_information(symbol=symbol)
    for future in futures:
        amount = future["positionAmt"]
        if amount != "0":  # if there is position
            open_position_side = None
            if future["entryPrice"] > future["liquidationPrice"]:
                open_position_side = "LONG"
                print(f"==> Long_x{future['leverage']}")
            else:
                open_position_side = "SHORT"
                print(f"==> Short_x{future['leverage']}")

            if side != open_position_side:
                print("==> CLOSING order")
                if side == "LONG":
                    buy(symbol, amount, client)
                else:
                    sell(symbol, amount, client)
            else:
                print("Warning: already opened position side and requested position side is same. Do nothing.")
                return False
    return True


def trade(client, data_msg):
    bar_close_decision = None
    chunks = data_msg.split(",")
    symbol = chunks[0]
    side = chunks[1]
    _type = chunks[2]
    print(f"symbol={symbol}")
    print(f"side={side}")
    print(f"type={_type}")
    if _type in ["BAR_CLOSE", "BAR_CROSS", "BAR_CROSS_SQ"]:
        bar_close_decision = side  # required for sync if side is revered within bar
        print(f"==> BAR_CLOSE={bar_close_decision}")

    if not strategy_exit(symbol, side):
        return

    time.sleep(0.1)
    print(f"==> OPENING {side} order")
    if side == "LONG":
        buy(symbol, AMOUNT, client)
    elif side == "SHORT":
        sell(symbol, AMOUNT, client)


if __name__ == "__main__":  # noqa: C901
    client, _ = check_binance_obj()
    balances = client.get_account()
    test = "DOGEUSDT,LONG"
    trade(client, test)
