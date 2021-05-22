#!/usr/bin/env python3

# altay: 1000 lot 4 kaldırac: toplam 4000 lot
# TODO: hard stop loss koy 10% zarara sonra kaldiraci arttirabilirsin
# TODO: min signal iterative 2 times check

import time
from pathlib import Path

from tools import log
from user_setup import check_binance_obj

HOME = str(Path.home())
AMOUNT = {}
AMOUNT["DOGEUSDT"] = 100
IS_PYRAMIDING = True
TAKE_PROFIT = 1.005
# TODO: dca 5/10/25  | 25teki coinlerle 1 dolarin altindaki coinleri cikar


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
            self.position_size = float(self.chunks[5])
            self.position_alert_msg = self.chunks[6]
            log(f"==> symbol={self.symbol}")
            log(f"==> side={self.side}")
            log(f"==> market_position={self.market_position}")
            log(f"==> prev_market_position={self.prev_market_position}")
            log(f"==> timenow={self.timenow}")
            log(f"==> position_size={self.position_size}")
            log(f"==> position_alert_msg={self.position_alert_msg}")
        except:
            pass


class BotHelper:
    def __init__(self, client):
        self.client = client

    def open_positions(self, is_print=False) -> bool:
        flag = False
        open_position_count = 0
        futures = self.client.futures_position_information()
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0" and float(future["unRealizedProfit"]) != 0.00000000:
                if future["entryPrice"] > future["liquidationPrice"]:
                    open_position_count += 1
                    if is_print:
                        print(future)
                    if not flag:
                        log(" * ", end="")
                        log("Open positions: ", color="blue", end="")
                        flag = True

                    log(f"{future['symbol']} ", color="cyan", end="")
        if flag:
            log("")
        return open_position_count

    def limit_order(self, symbol, _side):
        _entryPrice = None
        _amount = None

        futures = self.client.futures_position_information(symbol=symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0" and float(future["unRealizedProfit"]) != 0.00000000:
                _entryPrice = future["entryPrice"]
                _amount = future["positionAmt"]
                break

        decimal_count = len(str(_entryPrice).split(".")[1])
        _price = f"{float(_entryPrice) * TAKE_PROFIT:.{decimal_count}f}"
        create_order = client.futures_create_order(
            symbol=symbol, side=_side, type="LIMIT", timeInForce="GTC", quantity=abs(float(_amount)), price=_price,
        )
        print(create_order)

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
        time.sleep(1)
        self.limit_order(symbol, "SELL")

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
                else:
                    return "short"

    def strategy_exit(self, strategy):
        futures = self.client.futures_position_information(symbol=strategy.symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0" and float(future["unRealizedProfit"]) != 0.00000000:  # if there is position
                current_position_side = self.get_open_position_side(strategy.symbol)
                log(f"==> {current_position_side}_x{future['leverage']}")
                log("")
                if strategy.market_position == "flat":
                    log(f"==> CLOSING {current_position_side} position")
                    if current_position_side == "long":
                        if strategy.position_size > 0:
                            self.sell(strategy.symbol, strategy.position_size)
                        else:
                            self.sell(strategy.symbol, amount)
                    else:
                        if strategy.position_size > 0:
                            self.buy(strategy.symbol, strategy.position_size)
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
                    if not IS_PYRAMIDING:
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
            bot.buy(strategy.symbol, strategy.position_size)
        elif strategy.side == "sell":
            bot.sell(strategy.symbol, strategy.position_size)


if __name__ == "__main__":  # noqa: C901
    client, _ = check_binance_obj()
    balances = client.get_account()
    data_msg = "BAKEUSDTPERP,buy,long,flat,2021-05-28T18:45:01Z,2"
    trade(client, Strategy(data_msg))
