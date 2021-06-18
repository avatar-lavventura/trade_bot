#!/usr/bin/env python3

from pathlib import Path
from time import sleep

import ccxt  # noqa: E402
from _mongodb import Mongo
from broker._utils.tools import _colorize_traceback, get_decimal_count, log
from pymongo import MongoClient

from bot.user_setup import check_binance_obj

HOME = str(Path.home())
DCA = [5, 10, 25]
TP = 0.005
TAKE_PROFIT_LONG = 1.000 + TP
TAKE_PROFIT_SHORT = 1.000 - TP
#
INITIAL_USDT_QTY = 10
INITIAL_BTC_QTY = 0.00015


class Strategy:
    def __init__(self, data_msg):
        if "enter" in data_msg:
            log(data_msg, color="green")

        try:
            self.chunks = data_msg.split(",")
            if self.chunks[0] == "ALERT":
                self.symbol = self.chunks[1]
                self.side = self.chunks[2].upper()
                self.position_alert_msg = "enter"
                self.market_position = ""
            else:
                self.symbol = self.chunks[0]
                self.side = self.chunks[1].upper()
                self.position_alert_msg = self.chunks[2]
                self.market_position = ""
                self.prev_market_position = ""
                self.timenow = ""
                self.position_size = ""

            if "BTC" in self.symbol:
                self.market = "BTC"
                self.asset = self.symbol[:-3]  # remove BTC at the end
            elif "USDT" in self.symbol:
                self.symbol = self.symbol.replace("USDTPERP", "USDT")
                self.market = "USDT"
        except:
            pass

    def is_sell(self):
        return self.side == "SELL"

    def is_buy(self):
        return self.side == "BUY"


class BotHelper:
    def __init__(self, client):
        mc = MongoClient()
        self.mongoDB = Mongo(mc, mc["trader_bot"]["order"])
        self.client = client
        self.strategy = Strategy("")

    def symbol_price(self, symbol, default_type):
        exchange = ccxt.binance(
            {
                "options": {"default_type": default_type},
                "enableRateLimit": True,  # this option enables the built-in rate limiter
            }
        )
        try:
            return exchange.fetch_ticker(symbol)
        except ccxt.RequestTimeout as e:
            log("[" + type(e).__name__ + "]", color="red")
            log(str(e)[0:200])
            sleep(0.25)
            return self.symbol_price(symbol, default_type)
        except ccxt.DDoSProtection as e:
            log("[" + type(e).__name__ + "]", color="red")
            log(str(e.args)[0:200], color="red")
            sleep(0.25)
            return self.symbol_price(symbol, default_type)
        except ccxt.ExchangeNotAvailable as e:
            log("[" + type(e).__name__ + "]", color="red")
            log(str(e.args)[0:200], color="red")
            sleep(0.25)
            return self.symbol_price(symbol, default_type)
        except ccxt.ExchangeError as e:
            log("[" + type(e).__name__ + "]", color="red")
            log(str(e)[0:200], color="red")
            return False

    def opposite_side(self) -> str:
        if self.strategy.side == "BUY":
            return "SELL"
        elif self.strategy.side == "SELL":
            return "BUY"

    def _futures_cancel_order(self):
        """Cancel if already opened orders."""
        orders = self.client.futures_get_all_orders(symbol=self.strategy.symbol, type="LIMIT")
        if not orders:
            return

        for order in orders:
            if order["status"] == "NEW" and order["side"].lower() == self.opposite_side().lower():
                log("")
                log(f"==> Attempt to cancel order: {order}")
                self.client.futures_cancel_order(symbol=self.strategy.symbol, orderId=order["orderId"])

    def get_btc_open_positions(self):
        flag = False
        btc_open_position_size = 0
        balances = self.client.get_account()
        for balance in balances["balances"]:
            if float(balance["locked"]) > 0.0:
                btc_open_position_size += 1
                if not flag:
                    log(" * ", end="")
                    log("already opened BTC  positions: ", color="blue", end="")
                    flag = True

                log(f"{balance['asset']} ", color="cyan", end="")

        if flag:
            log("")
        return btc_open_position_size

    def get_usdt_open_positions(self, symbol=None, is_print=False):
        flag = False
        open_position_count = 0
        futures = self.client.futures_position_information()
        for future in futures:
            amount = abs(float(future["positionAmt"]))
            if amount > 0.0 and float(future["isolatedWallet"]) != "0":
                if future["symbol"] == symbol:
                    return True, 1

                open_position_count += 1
                if is_print:
                    print(future)
                if not flag and not symbol:
                    log(" * ", end="")
                    log("already opened USDT positions: ", color="blue", end="")
                    flag = True

                if not symbol:
                    log(f"{future['symbol'].replace('USDT', '')} ", color="cyan", end="")
        if flag:
            log("")
        return False, open_position_count

    def _limit(self, _amount, entry_price, decimal_count):
        try:
            order_flag = False
            _price = None
            if self.opposite_side() == "SELL":
                _price = f"{float(entry_price) * TAKE_PROFIT_LONG:.{decimal_count}f}"
                if _price > entry_price:
                    order_flag = True
                else:
                    log(f"E {_price} calculated wrong.", color="red")
            elif self.opposite_side() == "BUY":
                _price = f"{float(entry_price) * TAKE_PROFIT_SHORT:.{decimal_count}f}"
                if _price < entry_price:
                    order_flag = True
                else:
                    log(f"E {_price} calculated wrong.", color="red")

            if order_flag:
                log(f"| quantity={abs(float(_amount))}")
                order = self.client.futures_create_order(
                    symbol=self.strategy.symbol,
                    side=self.opposite_side(),
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=abs(float(_amount)),
                    price=_price,
                )
                log(order)
        except Exception as e:
            _colorize_traceback(e)
            if decimal_count > 0:
                self._limit(_amount, entry_price, decimal_count - 1)

    def asset_balance(self, asset=None) -> float:
        if not asset:
            asset = self.strategy.asset

        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] == asset:
                return float(balance["free"]) + float(balance["locked"])
        return 0.0

    def get_spot_entry(self):
        asset_balance = self.asset_balance()
        contracts = 0.0
        _sum = 0.0
        quantity = 0.0
        decimal_count = 0
        output = self.mongoDB.find_key("symbol", self.strategy.symbol)
        timestamp = output["timestamp"]
        log(f"timestamp={timestamp} | ", end="")
        log("\ntrade_price=\n", end="")
        for idx, trade in enumerate(reversed(self.client.get_my_trades(symbol=self.strategy.symbol))):
            _decimal_count = get_decimal_count(trade["price"])
            if _decimal_count > decimal_count:
                decimal_count = _decimal_count

            # TODO: trade["time"] >= timestamp gerek olmayabilir
            if trade["isBuyer"]:  # and trade["time"] >= timestamp:
                quantity += float(trade["qty"])
                if quantity > asset_balance:
                    break

                log(f"{trade['price']},{trade['qty']}\n", end="")
                _sum += float(trade["qty"]) * float(trade["price"])
                contracts += float(trade["qty"])

        entry_price = _sum / contracts
        _price = f"{entry_price:.{decimal_count}f}"
        limit_price = f"{float(_price) * TAKE_PROFIT_LONG:.{decimal_count}f}"
        log(f"quantity={asset_balance} | ", end="")
        log(f"entry_price={_price} | ", end="")
        log(f"limit_price={limit_price}")
        return limit_price, _price

    def spot_order_limit(self):
        log("attempting limit order for spot")
        try:
            limit_price, entry_price = self.get_spot_entry()
            orders = self.client.get_open_orders(symbol=self.strategy.symbol)
            for order in orders:
                self.client.cancel_order(symbol=self.strategy.symbol, orderId=order["orderId"])

            order = self.client.order_limit_sell(
                symbol=self.strategy.symbol, price=str(limit_price), quantity=self.asset_balance()
            )
            log(order)
        except Exception as e:
            _colorize_traceback(e, is_print_exc=False)
            # if "PRICE_FILTER" in str(e):
            #     decimal_count = get_decimal_count(limit_price)
            #     limit_price = f"{float(limit_price):.{decimal_count - 1}f}"
            #     log(f"==> re-opening sell order with new quantity={limit_price}")

            #     self.asset_balance(limit_price, asset_balance)
            # elif "Unknown order sent" in str(e):
            #     pass  # TODO try again

    def _order(self, quantity, _type="MARKET"):
        try:
            return self.client.futures_create_order(
                symbol=self.strategy.symbol, side=self.strategy.side, type=_type, quantity=quantity
            )
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e):
                log(f"E: {e} quantity={quantity}", color="red")
                decimal_count = get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal_count - 1}f}"
                log(f"==> re-opening sell order with new quantity={_quantity}")
                return self._order(_quantity)
            else:
                raise e

    def get_future_position(self, futures):
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0" and float(future["unRealizedProfit"]) != 0.00000000:
                return future["entryPrice"], future["positionAmt"]

        raise Exception("E: Order related to the symbol couldn't be found.")

    def futures_limit_order(self):
        try:
            self._futures_cancel_order()
        except Exception as e:
            log(f"E: Cancel order: {e}")

        log("==> Opening a limit order: attempt: ", end="")
        entry_price = None
        _amount = None
        for idx in range(50):
            try:
                if idx == 0:
                    log(f"attempt={idx} ", end="")
                else:
                    log(f"{idx} ", end="")

                futures = self.client.futures_position_information(symbol=self.strategy.symbol)
                entry_price, _amount = self.get_future_position(futures)
                break
            except Exception as e:
                _colorize_traceback(e, is_print_exc=False)
                sleep(1)

        log("")
        try:
            entry_price = entry_price.rstrip("0").rstrip(".") if "." in entry_price else entry_price
            log(f"entry_price={entry_price} ", end="")
            decimal_count = get_decimal_count(entry_price)
            self._limit(_amount, entry_price, decimal_count)
        except Exception as e:
            _colorize_traceback(e)

    def both_side_order(self) -> None:
        order = None
        try:
            if self.strategy.position_size == 0:
                raise Exception("E: Quantity less than zero.")

            order = self._order(quantity=self.strategy.position_size)
            log(order)
        except Exception as e:
            _colorize_traceback(e)
            raise e
        return order

    def sport_order(self, quantity, symbol=None, side=None):
        try:
            if not symbol:
                symbol = self.strategy.symbol

            if not side:
                side = self.strategy.side

            log(f"==> order_quantity={quantity}")
            return self.client.order_market(symbol=symbol, side=side, quantity=quantity)
        except Exception as e:
            _colorize_traceback(e)
            if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
                log(f"E: {e} quantity={quantity}", color="red")
                decimal_count = get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal_count - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                return self.sport_order(_quantity)
            else:
                raise e

    def get_initial_amount(self, initial_amount, _type):
        if initial_amount > 1.0:
            if _type == "BTC":
                return int(initial_amount)
            else:  # USDT
                return int(round(initial_amount))
        else:
            return format(initial_amount, ".4f")

    def check_position_size(self, current_price):
        """Handles order's notional must be no smaller than 5.0 (unless you choose
        reduce only)."""
        if self.strategy.position_size >= 1.0 and self.strategy.position_size * current_price < 5.0:
            self.strategy.position_size += 1

    def buy(self) -> bool:
        if self.strategy.market == "USDT":
            output = self.symbol_price(self.strategy.symbol.replace("USDT", "/USDT"), "future")
            current_price = output["last"]
            initial_amount = INITIAL_USDT_QTY / current_price
            self.strategy.position_size = self.get_initial_amount(initial_amount, "USDT")
            self.check_position_size(current_price)
            self.both_side_order()
            self.futures_limit_order()
        elif self.strategy.market == "BTC":
            output = self.symbol_price(self.strategy.symbol.replace("BTC", "/BTC"), "spot")
            current_price = output["last"]
            try:
                initial_amount = INITIAL_BTC_QTY / current_price
                self.strategy.position_size = self.get_initial_amount(initial_amount, "BTC")
                mongoDB_insert_flag = False
                if self.asset_balance() == 0.00000000:
                    mongoDB_insert_flag = True

                order = self.sport_order(self.strategy.position_size)
                log(order)
                if mongoDB_insert_flag:
                    self.mongoDB.add_item(self.strategy.symbol, order["transactTime"])
                    log(f"==> {order['transactTime']} added into mongoDB for {self.strategy.asset}")

                self.spot_order_limit()
            except Exception as e:
                log(f"E: {e}")
                raise e

    def sell(self) -> bool:
        default_type = "future"
        output = self.symbol_price(self.strategy.symbol.replace("USDT", "/USDT"), default_type)
        current_price = output["last"]
        initial_amount = INITIAL_USDT_QTY / current_price
        self.strategy.position_size = self.get_initial_amount(initial_amount, "USDT")
        self.check_position_size(current_price)
        self.both_side_order()
        sleep(1)
        if self.strategy.market == "USDT":
            try:
                self.futures_limit_order()
            except Exception as e:
                log(f"E: {e}", color="red")

    def get_open_position_side(self, _symbol) -> bool:
        futures = self.client.futures_position_information(symbol=_symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                if future["entryPrice"] > future["liquidationPrice"]:
                    return "long"
                else:
                    return "short"

    def trade(self):
        log("==> Attempt for trading. ", color="cyan")
        if self.strategy.market_position != "flat":
            log(f"==> Opening {self.strategy.side} order in the {self.strategy.market} market")
            if self.strategy.is_buy():
                self.buy()
            elif self.strategy.is_sell():
                self.sell()


if __name__ == "__main__":  # noqa: C901
    data_msg = ""
    client, _ = check_binance_obj()
    bot = BotHelper(client)
    bot.strategy = Strategy(data_msg)
    balances = client.get_account()
    # try:
    #     bot.trade()
    # except Exception as e:
    #     log(e)
