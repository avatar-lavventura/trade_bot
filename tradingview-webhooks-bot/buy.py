#!/usr/bin/env python3

# altay: 1000 lot 4 kaldırac: toplam 4000 lot
# TODO: hard stop loss koy 10% zarara sonra kaldiraci arttirabilirsin
# TODO: min signal iterative 2 times check

import time
from pathlib import Path
from user_setup import check_binance_obj
from utils import log

HOME = str(Path.home())
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
                else:
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
        return

    time.sleep(0.1)
    if strategy.market_position != "flat":
        log(f"==> OPENING {strategy.side} order")
        if strategy.side == "buy":
            bot.buy(strategy.symbol, AMOUNT[strategy.symbol])
        elif strategy.side == "sell":
            bot.sell(strategy.symbol, AMOUNT[strategy.symbol])


if __name__ == "__main__":  # noqa: C901
    client, _ = check_binance_obj()
    balances = client.get_account()
    data_msg = "DOGEUSDTPERP,buy,long,flat"
    trade(client, Strategy(data_msg))
