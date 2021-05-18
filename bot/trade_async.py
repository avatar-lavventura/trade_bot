#!/usr/bin/env python3

import time
from time import sleep

import ccxt
from _mongodb import Mongo
from bot_helper_async import TP, BotHelperAsync
from pymongo import MongoClient

from bot import helper
from bot.config import config
from ebloc_broker.broker._utils.tools import _colorize_traceback, _time, get_decimal_count, log

is_trade = True


class Strategy:
    def __init__(self, data_msg, is_print=True):
        if "enter" in data_msg:
            if is_print:
                log(f" * {_time()} ", end="")
                _join = data_msg.split(", (", 1)[0].split(",")[0:4]
                log(",".join(_join), "green")

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
                self.position_size = 0

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

    def is_buy(self):
        return self.side == "BUY"

    def is_sell(self):
        return self.side == "SELL"


class BotHelper:
    def __init__(self, client, discord_client=None):
        mc = MongoClient()
        self.mongoDB = Mongo(mc, mc["trader_bot"]["order"])
        self.client = client
        self.strategy = Strategy("")
        self.bot_async = BotHelperAsync()
        if discord_client:
            self.discord_client = discord_client

    async def symbol_price(self, symbol, default_type):
        try:
            if default_type == "future:":
                return await helper.exchange.future.fetch_ticker(symbol)
            else:
                return await helper.exchange.spot.fetch_ticker(symbol)
        except ccxt.RequestTimeout as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            sleep(0.25)
            return await self.symbol_price(symbol, default_type)
        except ccxt.DDoSProtection as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            sleep(0.25)
            return await self.symbol_price(symbol, default_type)
        except ccxt.ExchangeNotAvailable as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            sleep(0.25)
            return await self.symbol_price(symbol, default_type)
        except ccxt.ExchangeError as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            return False

    def opposite_side(self) -> str:
        if self.strategy.side == "BUY":
            return "SELL"
        elif self.strategy.side == "SELL":
            return "BUY"

    def _futures_cancel_order(self):
        """Cancel if already opened orders."""
        orders = self.client.futures_get_all_orders(symbol=self.strategy.symbol.replace("/", ""), type="LIMIT")
        if not orders:
            return

        for order in orders:
            if order["status"] == "NEW" and order["side"].lower() == self.opposite_side().lower():
                log(f"==> Attempt to cancel order: {order}")
                self.client.futures_cancel_order(symbol=self.strategy.symbol.replace("/", ""), orderId=order["orderId"])

    def get_btc_open_positions(self):
        flag = False
        btc_open_position_size = 0
        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] not in ["BTC", "BNB", "USDT"]:
                if float(balance["locked"]) > 0.0 or float(balance["free"]) > 0.0:
                    # TODO: check float(balance["free"]) USDT value if > 1.0 USDT
                    btc_open_position_size += 1
                    if not flag:
                        flag = True

        return btc_open_position_size

    def get_exchange_future_timestamp(self):
        self.unix_timestamp_ms = helper.exchange.get_future_timestamp()
        self.bar_index = int(int((self.unix_timestamp_ms - 1) / 900))

    async def is_usdt_open(self, symbol, all_positions_log=False) -> bool:
        future_positions = await helper.exchange.future.fetch_positions()
        self.get_exchange_future_timestamp()
        if all_positions_log:
            for position in future_positions:
                initial_margin = abs(float(position["info"]["isolatedWallet"]))
                if initial_margin > 0.0:
                    log(f"{position['symbol']} | ", "blue", end="")

        for position in future_positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                if symbol and symbol.replace("/", "") == position["symbol"].replace("/", ""):
                    # TODO: check position["timestamp"] is it on next bar index && positionInitialMargin < 20 USD
                    return True
        return False

    async def get_usdt_open_position_count(self, is_print=False) -> int:
        count = 0
        try:
            future_positions = await helper.exchange.future.fetch_positions()
        except Exception as e:
            _colorize_traceback(e)
            time.sleep(60)
            raise e

        for position in future_positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                count += 1
                if is_print:
                    log(position, "blue")

        return count

    def _limit(self, _amount, entry_price, decimal_count):
        try:
            order_flag = False
            _price = None
            if self.opposite_side() == "SELL":
                _price = f"{float(entry_price) * TP.get_profit_amount('long', _amount):.{decimal_count}f}"
                if _price > entry_price:
                    order_flag = True
                else:
                    log(f"E: limit={_price}, decimal={decimal_count} calculated wrong.")
            elif self.opposite_side() == "BUY":
                _price = f"{float(entry_price) * TP.get_profit_amount('short', _amount):.{decimal_count}f}"
                if _price < entry_price:
                    order_flag = True
                else:
                    log(f"E: limit={_price}, decimal={decimal_count} calculated wrong.")

            if order_flag:
                log(f"| quantity={abs(float(_amount))}")
                order = self.client.futures_create_order(
                    symbol=self.strategy.symbol.replace("/USDT", "USDT"),
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
        limit_price = f"{float(_price) * TP.get_profit_amount('long'):.{decimal_count}f}"
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
            _colorize_traceback(e, is_print_exc=False)
            # if "PRICE_FILTER" in str(e):
            #     decimal_count = get_decimal_count(limit_price)
            #     limit_price = f"{float(limit_price):.{decimal_count - 1}f}"
            #     log(f"==> re-opening sell order with new quantity={limit_price}")

            #     self.asset_balance(limit_price, asset_balance)
            # elif "Unknown order sent" in str(e):
            #     pass  # TODO try again

    async def _order(self, quantity, _type="MARKET"):
        """Opens futures orders in given direction."""
        try:
            await self.bot_async.set_leverage(self.strategy.symbol, config.INITIAL_LEVERAGE)
            return self.client.futures_create_order(
                symbol=self.strategy.symbol.replace("/USDT", "USDT"),
                side=self.strategy.side,
                type=_type,
                quantity=quantity,
            )
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e):
                log(f"E: {e} quantity={quantity}", "red")
                decimal_count = get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal_count - 1}f}"
                log(f"==> re-opening sell order with new quantity={_quantity}")
                return await self._order(_quantity)
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

        log("==> Opening a limit order: ", end="")
        entry_price = None
        _amount = None
        for idx in range(50):
            try:
                log(f"attempt={idx} ", "cyan", end="")
                _symbol = self.strategy.symbol.replace("/USDT", "USDT")
                futures = self.client.futures_position_information(symbol=_symbol)
                entry_price, _amount = self.get_future_position(futures)
                break
            except Exception as e:
                _colorize_traceback(e, is_print_exc=False)
                sleep(1)

        log("")
        try:
            entry_price = entry_price.rstrip("0").rstrip(".") if "." in entry_price else entry_price
            log(f"entry={entry_price} ", end="")
            decimal_count = get_decimal_count(entry_price)
            self._limit(_amount, entry_price, decimal_count)
        except Exception as e:
            _colorize_traceback(e)

    async def both_side_order(self) -> None:
        """Both side order for futures."""
        _symbol = self.strategy.symbol.replace("/USDT", "USDT")
        if await self.is_usdt_open(_symbol, all_positions_log=True):
            raise Exception(f"E: Already open position for {_symbol}")

        order = None
        try:
            if self.strategy.position_size == 0:
                raise Exception("E: Quantity less than zero.")

            order = await self._order(quantity=self.strategy.position_size)
            log(order)
        except Exception as e:
            _colorize_traceback(e)
            raise e
        return order

    def spot_order(self, quantity: float, symbol=None, side=None):
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
                    return self.spot_order(float(_quantity))
                else:
                    log("E: quantity is zero, nothing to do.")
            elif "Filter failure: MIN_NOTIONAL" == getattr(e, "message", repr(e)) and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f"==> re-opening {side} order, quantity={quantity}")
                return self.spot_order(float(quantity))
            else:
                _colorize_traceback(e)
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
        """Handles order's notional must be no smaller than 5.0 (unless you choose
        reduce only)."""
        log(f"==> [update_position_size] current_price={current_price} position_size={self.strategy.position_size}")
        if self.strategy.position_size >= 1.0 and self.strategy.position_size * current_price < 5.0:
            self.strategy.position_size += 1
            log(f"update_position_size => current_price={current_price} position_size={self.strategy.position_size}")

    async def calculate_futures_position_size(self):
        self.strategy.position_size = 0
        output = await self.symbol_price(self.strategy.symbol, "future")
        current_price = output["last"]
        if current_price < config.IGNORE_BELOW_USDT:
            raise Exception(
                f"Price of {self.strategy.symbol} is below {config.IGNORE_BELOW_USDT}$. current_price={current_price}."
                " PASS"
            )

        initial_amount = config.INITIAL_USDT_QTY / current_price
        self.strategy.position_size = float(self.get_initial_amount(initial_amount, "USDT"))
        self.update_position_size(current_price)
        # TODO: re-check `self.strategy.position_size * order` > INITIAL_ENTER_PRICE

    async def buy(self) -> bool:
        if self.strategy.market == "USDTPERP":
            await self.both_side_order()
            self.futures_limit_order()
        elif self.strategy.market == "BTC":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            current_price = output["last"]
            try:
                initial_amount = config.INITIAL_BTC_QTY / current_price
                self.strategy.position_size = self.get_initial_amount(initial_amount, "BTC")
                order = self.spot_order(float(self.strategy.position_size))
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
                _colorize_traceback(e)
                raise e

    async def sell(self) -> bool:
        await self.both_side_order()
        sleep(1)
        if self.strategy.market == "USDTPERP":
            try:
                self.futures_limit_order()
            except Exception as e:
                _colorize_traceback(e)

    def get_open_position_side(self, _symbol) -> bool:
        futures = self.client.futures_position_information(symbol=_symbol)
        for future in futures:
            amount = future["positionAmt"]
            if amount != "0":  # if there is position
                if future["entryPrice"] > future["liquidationPrice"]:
                    return "long"
                else:
                    return "short"

    async def trade_async(self):
        try:
            if self.strategy.market_position != "flat":
                if self.strategy.market == "USDTPERP":
                    await self.calculate_futures_position_size()

                log("==> Attempt for trading", "cyan")
                log(
                    f"==> Opening {self.strategy.side} order in the {self.strategy.market} market for"
                    f" {self.strategy.asset} {self.strategy.symbol} size={self.strategy.position_size}"
                )
                if self.strategy.is_buy():
                    await self.buy()
                elif self.strategy.is_sell():
                    await self.sell()
        except Exception as e:
            log(str(e), "yellow")

    async def check_on_going_positions(self, strategy) -> bool:
        if strategy.market == "USDTPERP":
            usdt_open_position_size = await self.get_usdt_open_position_count()
            if usdt_open_position_size >= config.USDT_MAX_POSITION_NUMBER:
                # log(f"Warning: There is already ongoing {USDT_MAX_POSITION_NUMBER} of positions.")
                return True
        elif strategy.market == "BTC":
            btc_open_position_size = self.get_btc_open_positions()
            if btc_open_position_size >= config.SPOT_MAX_POSITION_NUMBER:
                # log(f"Warning: There is already ongoing {SPOT_MAX_POSITION_NUMBER} of positions")
                return True
        return False

    async def _trade(self, strategy):
        if strategy.market_position == "flat":
            live_pos_side = self.get_open_position_side(strategy.symbol)
            log(f"==> live_pos_side={live_pos_side}")
            # if strategy.prev_market_position == live_pos_side:
            #     self.strategy_exit(strategy)
        else:
            is_open = False
            if strategy.market == "USDTPERP":
                is_open = await self.is_usdt_open(strategy.symbol)
            elif strategy.market == "BTC":
                balances = self.client.get_account()
                for balance in balances["balances"]:
                    if balance["asset"] == strategy.asset and float(balance["locked"]) > 0.0:
                        is_open = True
                        break

            if not is_open:
                try:
                    self.strategy = strategy
                    await self.trade_async()
                    log("END")
                except Exception as e:
                    _colorize_traceback(e)
            else:
                log(f"   already open position {self.unix_timestamp_ms} {self.bar_index}")

    async def trade(self):
        try:
            await self.trade_async()
        except Exception as e:
            log(str(e))
        finally:
            await helper.exchange.future.close()
            await helper.exchange.spot.close()

    async def trade_main(self, data_msg, discord_client=None):
        if "enter_" in data_msg:
            log(data_msg, "green")
            await self.discord_client.send_msg(data_msg)
            return True

        strategy = Strategy(data_msg, is_print=True)
        try:
            strategy.position_alert_msg
        except:
            return True

        output = await self.check_on_going_positions(strategy)
        if "enter" not in strategy.position_alert_msg or strategy.symbol == "TEST" or output:
            pass
        elif strategy.market == "BTC" and strategy.is_sell():
            log("Warning: Ignore BTC pair, no need to sell.")
        elif is_trade:
            await self._trade(strategy)

        return True
