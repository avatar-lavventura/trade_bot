#!/usr/bin/env python3

# altay: 1000 lot 4 kaldırac: toplam 4000 lot
# TODO: hard stop loss koy 10% zarara sonra kaldiraci arttirabilirsin
# TODO: min signal iterative 2 times check

import time
from pathlib import Path

from tools import log
from user_setup import check_binance_obj

HOME = str(Path.home())
<<<<<<< HEAD
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
||||||| parent of db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)
AMOUNT = {}
AMOUNT["DOGEUSDT"] = 1240
# AMOUNT = 8000  # 1000Shibi
# TODO: 300$ lik al yap


class Strategy:
    def __init__(self, data_msg):
        print(data_msg)
        # {{ticker}},{{strategy.order.action}},{{strategy.market_position}},{{strategy.prev_market_position}},{{timenow}}
        self.chunks = data_msg.split(",")
        self.symbol = self.chunks[0].replace("PERP", "")
        self.side = self.chunks[1]
        self.market_position = self.chunks[2]
        self.prev_market_position = self.chunks[3]
        self.timenow = self.chunks[4]
        log(f"==> symbol={self.symbol}")
        log(f"==> side={self.side}")
        log(f"==> market_position={self.market_position}")
        log(f"==> prev_market_position={self.prev_market_position}")
        log(f"==> timenow={self.timenow}")


class BotHelper:
    def __init__(self, client):
        self.client = client

    def buy(self, symbol, amount):
        amount = abs(float(amount))
        try:
            order = self.client.futures_create_order(
                symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=False
            )
        except:
            order = self.client.futures_create_order(
                symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=True
            )

        print(f"{order}\n")

    def sell(self, symbol, amount):
        amount = abs(float(amount))
        print(f"amount={amount}")
        try:
            order = self.client.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=amount)
            print(f"{order}\n")
        except:
            try:
                order = self.client.futures_create_order(
                    symbol=symbol, side="SELL", type="MARKET", quantity=amount, reduceOnly=True
                )
                print(f"{order}\n")
            except Exception as e:
                print(str(e))  # ReduceOnly Order is rejected or // Margin is insufficient.

    def strategy_exit(self, strategy):
        futures = self.client.futures_position_information(symbol=strategy.symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                open_position_side = None
                if future["entryPrice"] > future["liquidationPrice"]:
                    open_position_side = "long"
=======
AMOUNT = {}
AMOUNT["DOGEUSDT"] = 100


class Strategy:
    def __init__(self, data_msg):
        log(data_msg, color="green")
        try:
            self.chunks = data_msg.split(",")
            self.symbol = self.chunks[0].replace("PERP", "")
            self.side = self.chunks[1]
            self.market_position = self.chunks[2]
            self.prev_market_position = self.chunks[3]
            self.timenow = self.chunks[4]
            self.position_size = self.chunks[5]
            log(f"==> symbol={self.symbol}")
            log(f"==> side={self.side}")
            log(f"==> market_position={self.market_position}")
            log(f"==> prev_market_position={self.prev_market_position}")
            log(f"==> timenow={self.timenow}")
            log(f"==> position_size={self.position_size}")
        except:
            pass


class BotHelper:
    def __init__(self, client):
        self.client = client

    def buy(self, symbol, amount):
        amount = abs(float(amount))
        try:
            order = self.client.futures_create_order(
                symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=False
            )
        except:
            order = self.client.futures_create_order(
                symbol=symbol, side="BUY", type="MARKET", quantity=amount, reduceOnly=True
            )

        log(f"{order}\n")

    def sell(self, symbol, amount):
        amount = abs(float(amount))
        log(f"amount={amount}")
        try:
            order = self.client.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=amount)
            log(f"{order}\n")
        except:
            try:
                order = self.client.futures_create_order(
                    symbol=symbol, side="SELL", type="MARKET", quantity=amount, reduceOnly=True
                )
                log(f"{order}\n")
            except Exception as e:
                log(str(e), color="red")  # ReduceOnly Order is rejected or // Margin is insufficient.

    def get_open_position_side(self, _symbol) -> bool:
        futures = self.client.futures_position_information(symbol=_symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                if future["entryPrice"] > future["liquidationPrice"]:
                    return "long"
>>>>>>> db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)
                else:
<<<<<<< HEAD
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
||||||| parent of db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)
                    open_position_side = "short"

                print(f"==> {open_position_side}_x{future['leverage']}")
                if strategy.market_position == "flat":
                    log(f"==> CLOSING {open_position_side} position")
                    if open_position_side == "long":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                elif strategy.market_position != open_position_side:
                    log(f"==> CLOSING {open_position_side} position")
                    if strategy.market_position == "short":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                else:
                    log("Warning: already opened position side and requested position side is same. Do nothing.")
                    return False
        return True


def trade(client, strategy):
    log("==> Attempt for trading")
    bot = BotHelper(client)
    if not bot.strategy_exit(strategy):
=======
                    return "short"

    def strategy_exit(self, strategy):
        futures = self.client.futures_position_information(symbol=strategy.symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                current_position_side = self.get_open_position_side(strategy.symbol)
                log(f"==> {current_position_side}_x{future['leverage']}")
                log("")
                if strategy.market_position == "flat":
                    log(f"==> CLOSING {current_position_side} position")
                    if current_position_side == "long":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                elif strategy.market_position != current_position_side:
                    log(f"==> CLOSING {current_position_side} position")
                    if strategy.market_position == "short":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                else:
                    log(
                        "Warning: already opened position, where on going position side and requested position side are"
                        " the same. Do nothing."
                    )
                    log(future)
                    return False
        return True


def trade(client, strategy):
    log("==> Attempt for trading")
    bot = BotHelper(client)
    if not bot.strategy_exit(strategy):
>>>>>>> db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)
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
