#!/usr/bin/env python3

# altay: 1000 lot 4 kaldırac: toplam 4000 lot
# TODO: hard stop loss koy 10% zarara sonra kaldiraci arttirabilirsin
# TODO: min signal iterative 2 times check

import time
from pathlib import Path

from user_setup import check_binance_obj

HOME = str(Path.home())
AMOUNT = 20


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
        print(f"symbol={self.symbol}")
        print(f"side={self.side}")
        print(f"market_position={self.market_position}")
        print(f"prev_market_position={self.prev_market_position}")
        print(f"timenow={self.timenow}")


class BotHelper:
    def __init__(self, client):
        self.client = client

    def buy(self, symbol, amount):
        amount = abs(float(amount))
        print(f"amount={amount}")
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
        except:
            order = self.client.futures_create_order(
                symbol=symbol, side="SELL", type="MARKET", quantity=amount, reduceOnly=True
            )

        print(f"{order}\n")

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
                    print(f"==> CLOSING {open_position_side} position")
                    if open_position_side == "long":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                elif strategy.market_position != open_position_side:
                    print(f"==> CLOSING {open_position_side} position")
                    if strategy.market_position == "short":
                        self.sell(strategy.symbol, amount)
                    else:
                        self.buy(strategy.symbol, amount)
                else:
                    print("Warning: already opened position side and requested position side is same. Do nothing.")
                    return False
        return True


def trade(client, strategy):
    print("==> Attempt for trading")
    bot = BotHelper(client)
    if not bot.strategy_exit(strategy):
        return

    time.sleep(0.1)
    if strategy.market_position != "flat":
        print(f"==> OPENING {strategy.side} order")
        if strategy.side == "buy":
            bot.buy(strategy.symbol, AMOUNT)
        elif strategy.side == "sell":
            bot.sell(strategy.symbol, AMOUNT)


if __name__ == "__main__":  # noqa: C901
    client, _ = check_binance_obj()
    balances = client.get_account()
    data_msg = "DOGEUSDTPERP,buy,long,flat"
    trade(client, Strategy(data_msg))
