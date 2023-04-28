#!/usr/bin/env python3

import asyncio  # noqa
import os
from pathlib import Path
from time import sleep

import ccxt
from _mongodb import Mongo
from broker._utils.tools import _time, get_decimal_count, log, print_tb
from dotenv import load_dotenv
from pymongo import MongoClient

import bot.helper as helper
from bot.user_setup import check_binance_obj

HOME = str(Path.home())
DCA = [5, 10, 25]
load_dotenv(override=True)
INITIAL_USDT_QTY = float(os.getenv("INITIAL_USDT_QTY"))
initial_btc_quantity = float(os.getenv("initial_btc_quantity"))
TP = float(os.getenv("TP"))
TAKE_PROFIT_LONG = 1.000 + TP
TAKE_PROFIT_SHORT = 1.000 - TP
BTC_MAX_POS_NUMBER = int(os.getenv("BTC_MAX_POS_NUMBER"))
USDT_MAX_POS_NUMBER = int(os.getenv("USDT_MAX_POS_NUMBER"))
is_trade = True
data_msg_temp = None


class Strategy:
    def __init__(self, data_msg, is_print=True):
        if "enter" in data_msg:
            if is_print:
                log(f" * {_time()} ", end="")
                log(",".join(data_msg.split(", (", 1)[0].split(",")[0:3]), color="green", end="")
                log(" |", end="")

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
                self.asset = self.symbol[:-3]  # removes BTC at the end
                self.symbol = self.symbol.replace("BTC", "/BTC")
            elif "USDT" in self.symbol:
                self.market = "USDTPERP"
                self.asset = self.symbol[:-8]  # removes USDTPERP at the end
                self.symbol = self.symbol.replace("USDTPERP", "/USDT")
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

    def set_leverage(self, symbol):
        try:
            leverage = 1
            market = helper.exchange.future.market(symbol)
            response = helper.exchange.future.fapiPrivate_post_leverage({"symbol": market["id"], "leverage": leverage})
            log(response, color="cyan")
            response = helper.exchange.future.fapiPrivate_post_margintype(
                {"symbol": market["id"], "marginType": "ISOLATED"}
            )
            log(response, color="cyan")
        except Exception as e:
            if "No need to change margin type." not in str(e):
                print_tb(e)

    def symbol_price(self, symbol, default_type):
        if symbol == "1000SHIB/USDT":
            symbol = "SHIB/USDT"

        try:
            if default_type == "future:":
                return helper.exchange.future.fetch_ticker(symbol)
            else:
                return helper.exchange.spot.fetch_ticker(symbol)
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
        else:  # self.strategy.side == "SELL":
            return "BUY"

    def usdtperp_cancel_order(self):
        """Cancel if already opened orders."""
        orders = self.client.futures_get_all_orders(symbol=self.strategy.symbol.replace("/", ""), type="LIMIT")
        if not orders:
            return

        for order in orders:
            if order["status"] == "NEW" and order["side"].lower() == self.opposite_side().lower():
                log("")
                log(f"==> Attempt to cancel order: {order}")
                self.client.futures_cancel_order(symbol=self.strategy.symbol.replace("/", ""), orderId=order["orderId"])

    def get_btc_open_positions(self):
        flag = False
        btc_open_position_size = 0
        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] not in ["BTC", "BNB"]:
                if float(balance["locked"]) > 0.0 or float(balance["free_usdt"]) > 0.0:
                    # TODO: check float(balance["free_usdt"]) USDT value if > 1.0 USDT
                    btc_open_position_size += 1
                    if not flag:
                        flag = True

        return btc_open_position_size

    def is_usdt_open_open(self, symbol) -> bool:
        future_positions = helper.exchange.future.fetch_positions()
        for position in future_positions:
            initial_margin = abs(float(position["info"]["positionInitialMargin"]))
            if initial_margin > 0.0:
                if symbol and symbol.replace("/", "") == position["symbol"].replace("/", ""):
                    return True
        return False

    def get_futures_open_position_count(self, is_print=False) -> int:
        count = 0
        future_positions = helper.exchange.future.fetch_positions()
        for position in future_positions:
            initial_margin = abs(float(position["info"]["positionInitialMargin"]))
            if initial_margin > 0.0:
                count += 1
                if is_print:
                    log(position, color="blue")

        return count

    def _limit(self, _amount, entry_price, decimal_count):
        try:
            order_flag = False
            _price = None
            if self.opposite_side() == "SELL":
                _price = f"{float(entry_price) * TAKE_PROFIT_LONG:.{decimal_count}f}"
                if _price > entry_price:
                    order_flag = True
                else:
                    log(f"E: limit={_price}, decimal={decimal_count} calculated wrong.")
            elif self.opposite_side() == "BUY":
                _price = f"{float(entry_price) * TAKE_PROFIT_SHORT:.{decimal_count}f}"
                if _price < entry_price:
                    order_flag = True
                else:
                    log(f"E: limit={_price}, decimal={decimal_count} calculated wrong.")

            if order_flag:
                _symbol = self.strategy.symbol.replace("/USDT", "USDT")
                log(f"| quantity={abs(float(_amount))}")
                order = self.client.futures_create_order(
                    symbol=_symbol,
                    side=self.opposite_side(),
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=abs(float(_amount)),
                    price=_price,
                )
                log(order)
        except Exception as e:
            print_tb(e)
            if decimal_count > 0:
                self._limit(_amount, entry_price, decimal_count - 1)

    def asset_balance(self, asset=None) -> float:
        if not asset:
            asset = self.strategy.asset

        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] == asset:
                return float(balance["free_usdt"]) + float(balance["locked"])
        return 0.0

    def get_spot_entry(self):
        asset_balance = self.asset_balance()
        contracts = 0.0
        _sum = 0.0
        quantity = 0.0
        decimal_count = 0
        # try:
        #     output = self.mongoDB.find_key("asset", self.strategy.asset)
        #     timestamp = output["timestamp"]
        #     log(f"timestamp={timestamp} | ", end="")
        # except:
        #     pass

        log("\ntrade_price=", end="")
        for idx, trade in enumerate(reversed(self.client.get_my_trades(symbol=self.strategy.symbol.replace("/", "")))):
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
        log(f"entry={_price} | ", end="")
        log(f"limit={limit_price}")
        return limit_price, _price

    def spot_order_limit(self):
        log("attempting limit order for spot")
        try:
            limit_price, entry_price = self.get_spot_entry()
            orders = self.client.get_open_orders(symbol=self.strategy.symbol.replace("/", ""))
            for order in orders:
                self.client.cancel_order(symbol=self.strategy.symbol.replace("/", ""), orderId=order["orderId"])

            order = self.client.order_limit_sell(
                symbol=self.strategy.symbol.replace("/", ""), price=str(limit_price), quantity=self.asset_balance()
            )
            log(order)
        except Exception as e:
            print_tb(e, is_print_exc=False)
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
                symbol=self.strategy.symbol.replace("/USDT", "USDT"),
                side=self.strategy.side,
                type=_type,
                quantity=quantity,
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
            self.usdtperp_cancel_order()
        except Exception as e:
            log(f"E: Cancel order: {e}")

        log("==> Opening a limit order: ", end="")
        entry_price = None
        _amount = None
        for idx in range(50):
            try:
                log(f"attempt={idx} ", end="", color="cyan")
                _symbol = self.strategy.symbol.replace("/USDT", "USDT")
                futures = self.client.futures_position_information(symbol=_symbol)
                entry_price, _amount = self.get_future_position(futures)
                break
            except Exception as e:
                print_tb(e, is_print_exc=False)
                sleep(1)

        log("")
        try:
            entry_price = entry_price.rstrip("0").rstrip(".") if "." in entry_price else entry_price
            log(f"entry={entry_price} ", end="")
            decimal_count = get_decimal_count(entry_price)
            self._limit(_amount, entry_price, decimal_count)
        except Exception as e:
            print_tb(e)

    def both_side_order(self) -> None:
        _symbol = self.strategy.symbol.replace("/USDT", "USDT")
        if self.is_usdt_open_open(_symbol):
            raise Exception(f"E: Already open position for {_symbol}")

        order = None
        try:
            if self.strategy.position_size == 0:
                raise Exception("E: Quantity less than zero.")

            if self.strategy.symbol.replace("/", "") == "1000SHIBUSDT":
                self.strategy.position_size = int(round(self.strategy.position_size / 1000))

            # Opens order
            order = self._order(quantity=self.strategy.position_size)
            log(order)
        except Exception as e:
            print_tb(e)
            raise e
        return order

    def spot_order(self, quantity, symbol=None, side=None):
        if symbol:
            self.strategy.symbol = symbol

        if side:
            self.strategy.side = side

        try:
            if not symbol:
                symbol = self.strategy.symbol

            if not side:
                side = self.strategy.side

            log(f"==> order_quantity={quantity}")
            return self.client.order_market(symbol=symbol.replace("/", ""), side=side, quantity=quantity)
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
                log(f"E: {e} quantity={quantity}")
                decimal_count = get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal_count - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return self.spot_order(_quantity)
                else:
                    log("E: quantity is zero, nothing to do.")
            elif "Filter failure: MIN_NOTIONAL" == getattr(e, "message", repr(e)) and quantity >= 1:
                quantity += 0.10
                log(f"==> re-opening {side} order, quantity={quantity}")
                return self.spot_order(quantity)
            else:
                print_tb(e)
                raise e

    def get_initial_amount(self, initial_amount, _type):
        if initial_amount > 1.0:
            if _type == "BTC":
                return int(initial_amount)
            else:  # USDTPERP
                return int(round(initial_amount))
        else:
            return float(format(initial_amount, ".4f"))

    def update_position_size(self, current_price):
        """Handle order's notional."""
        if self.strategy.position_size >= 1.0 and self.strategy.position_size * current_price < 5.0:
            self.strategy.position_size += 1

    def buy(self) -> bool:
        if self.strategy.market == "USDTPERP":
            output = self.symbol_price(self.strategy.symbol, "future")
            current_price = output["last"]
            initial_amount = INITIAL_USDT_QTY / current_price
            self.strategy.position_size = float(self.get_initial_amount(initial_amount, "USDT"))
            self.update_position_size(current_price)
            self.both_side_order()
            self.futures_limit_order()
        elif self.strategy.market == "BTC":
            output = self.symbol_price(self.strategy.symbol, "spot")
            current_price = output["last"]
            try:
                initial_amount = initial_btc_quantity / current_price
                self.strategy.position_size = self.get_initial_amount(initial_amount, "BTC")
                order = self.spot_order(self.strategy.position_size)
                log(order)
                # mongoDB_insert_flag = False
                # if self.asset_balance() == 0.00000000:
                #    mongoDB_insert_flag = True
                #
                # if mongoDB_insert_flag:
                #    self.mongoDB.add_item(self.strategy.asset, order["transactTime"])
                #    log(f"==> {order['transactTime']} added into mongoDB for {self.strategy.asset} in BTC")
                self.spot_order_limit()
            except Exception as e:
                print_tb(e)
                raise e

    def sell(self) -> bool:
        default_type = "future"
        output = self.symbol_price(self.strategy.symbol, default_type)
        current_price = output["last"]
        initial_amount = INITIAL_USDT_QTY / current_price
        self.strategy.position_size = self.get_initial_amount(initial_amount, "USDT")
        self.update_position_size(current_price)
        self.both_side_order()
        sleep(1)
        if self.strategy.market == "USDTPERP":
            try:
                self.futures_limit_order()
            except Exception as e:
                print_tb(e)

    def get_open_position_side(self, _symbol) -> bool:
        futures = self.client.futures_position_information(symbol=_symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                if future["entryPrice"] > future["liquidationPrice"]:
                    return "long"
                else:
                    return "short"

    def trade_async(self):
        log("==> Attempt for trading. ", color="cyan")
        try:
            if self.strategy.market_position != "flat":
                log(f"==> opening {self.strategy.side} order in the {self.strategy.market} market")
                if self.strategy.is_buy():
                    self.buy()
                elif self.strategy.is_sell():
                    self.sell()
        except Exception as e:
            log(str(e))

    def trade(self):
        try:
            self.trade_async()
        except Exception as e:
            log(str(e))
        finally:
            helper.exchange.future.close()
            helper.exchange.spot.close()

    def check_on_going_positions(self, strategy) -> bool:
        if strategy.market == "USDTPERP":
            usdt_open_position_size = self.get_futures_open_position_count()
            if usdt_open_position_size >= USDT_MAX_POS_NUMBER:
                # log(f"warning: There is already ongoing {USDT_MAX_POS_NUMBER} of positions.")
                return True
        elif strategy.market == "BTC":
            btc_open_position_size = self.get_btc_open_positions()
            if btc_open_position_size >= BTC_MAX_POS_NUMBER:
                # log(f"warning: There is already ongoing {BTC_MAX_POS_NUMBER} of positions")
                return True
        return False

    def _trade(self, strategy):
        if strategy.market_position == "flat":
            live_pos_side = self.get_open_position_side(strategy.symbol)
            log(f"==> live_pos_side={live_pos_side}")
            # if strategy.prev_market_position == live_pos_side:
            #     self.strategy_exit(strategy)
        else:
            is_open = False
            if strategy.market == "USDTPERP":
                is_open = self.is_usdt_open_open(strategy.symbol)
            elif strategy.market == "BTC":
                balances = self.client.get_account()
                for balance in balances["balances"]:
                    if balance["asset"] == strategy.asset and float(balance["locked"]) > 0.0:
                        is_open = True
                        break

            if not is_open:
                try:
                    self.strategy = strategy
                    self.trade_async()
                    log("SUCCESS")
                except Exception as e:
                    print_tb(e)

    def trade_main(self, data_msg):
        global data_msg_temp
        is_print = True
        if "enter" in data_msg:
            _data_msg = data_msg.split(", (", 1)[0].split(",")[0]
            if data_msg_temp != _data_msg:
                data_msg_temp = _data_msg
            else:  # prevents same alert messages to print
                is_print = False

        strategy = Strategy(data_msg, is_print)
        if "enter" in data_msg and is_print:
            future_positions = helper.exchange.future.fetch_positions()
            for position in future_positions:
                if abs(float(position["info"]["positionInitialMargin"])) > 0.0:
                    log(f" {position['symbol'].replace('/USDT', '')} ", end="", color="cyan")

            if len(future_positions) > 0:
                log("")

        try:
            strategy.position_alert_msg
        except:
            return True

        output = self.check_on_going_positions(strategy)
        if "enter" not in strategy.position_alert_msg or strategy.symbol == "TEST" or output:
            # log(f"warning: ignore, nothing to do. {strategy.position_alert_msg}")
            pass
        elif strategy.market == "BTC" and strategy.is_sell():
            log("warning: Ignore BTC pair, no need to sell.")
        elif is_trade:
            self._trade(strategy)

        return True


client, balances = check_binance_obj()
bot = BotHelper(client)


if __name__ == "__main__":
    data_msg = "MTLUSDTPERP,sell,enter,1.943"
    bot.strategy = Strategy(data_msg)
    balances = client.get_account()
    try:
        asyncio_loop = asyncio.get_event_loop()
        asyncio_loop.run_until_complete(bot.trade_main(data_msg))
    except Exception as e:
        print_tb(e)
