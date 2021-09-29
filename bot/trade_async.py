#!/usr/bin/env python3

# TODO: convert self.client.* into async calls
from contextlib import suppress

import ccxt
from _mongodb import Mongo
from bot_helper_async import TP, BotHelperAsync, TP_calculate
from filelock import FileLock
from pymongo import MongoClient

from bot import helper
from bot.binance_balance import _create_limit_order, _create_market_order
from bot.client_helper import DiscordClient
from bot.config import config
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import QuietExit, _colorize_traceback, _time, decimal_count

is_trade = True


class Strategy:
    def __init__(self, data_msg=""):
        self.symbol = ""
        self.market = ""
        self.unix_timestamp_ms: int = 0
        self.position_size: int = 0
        if "enter" in data_msg:
            log(f" * {_time()} ", end="")
            log(f"{data_msg}", "bold magenta", end="")

        with suppress(Exception):
            self.parse_data_msg(data_msg)

        if self.market in ["BTC", "USDT"]:
            if self.side == "SELL":
                raise QuietExit(f"E: Only BUY for {self.market} market")

    def parse_data_msg(self, data_msg):
        self.position_size = 0
        self.chunks = data_msg.split(",")
        self.side = self.chunks[1].upper()
        self.symbol = self.chunks[0]
        if "BTC" in self.symbol:
            self.market = "BTC"
            self.asset = self.symbol[:-3]  # removes BTC at the end
            self.symbol = self.symbol.replace("BTC", "/BTC")
            if self.side == "SELL":
                return
        elif "USDTPERP" in self.symbol:
            self.market = "USDTPERP"
            self.asset = self.symbol.replace("USDTPERP", "")
            self.symbol = self.symbol.replace("USDTPERP", "/USDT")
        elif "USDT" in self.symbol:
            self.market = "USDT"  # spot
            self.asset = self.symbol.replace("USDT", "")
            self.symbol = self.symbol.replace("USDT", "/USDT")
            if self.side == "SELL":
                return

        self.position_alert_msg = self.chunks[2]
        self.time_duration = ""
        self.time_duration = self.position_alert_msg.rsplit("_", 1)[1]
        self.current_bar_index = self.chunks[3]  # differs for each pair
        self.time = self.chunks[4]

    def is_buy(self):
        return self.side == "BUY"

    def is_sell(self):
        return self.side == "SELL"


class BotHelper:
    def __init__(self, client, discord_client=None) -> None:
        mc = MongoClient()
        self.mongoDB = Mongo(mc, mc["trader_bot"]["order"])
        self.unix_timestamp_ms: int = 0
        self.current_bar_index_local: int = 0
        self.client = client
        self.strategy = Strategy()
        self.bot_async = BotHelperAsync()
        if discord_client:
            self.discord_client: "DiscordClient" = discord_client

    async def symbol_price(self, symbol, _type):
        try:
            if _type == "future:":
                return await helper.exchange.future.fetch_ticker(symbol)
            else:
                return await helper.exchange.spot.fetch_ticker(symbol)
        except ccxt.RequestTimeout as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            await _sleep(0.25)
            return await self.symbol_price(symbol, _type)
        except ccxt.DDoSProtection as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            await _sleep(0.25)
            return await self.symbol_price(symbol, _type)
        except ccxt.ExchangeNotAvailable as e:
            log(f"[{type(e).__name__}] {str(e)[0:200]}", "red")
            await _sleep(0.25)
            return await self.symbol_price(symbol, _type)
        except ccxt.ExchangeError as e:
            raise e

    def opposite_side(self) -> str:
        if self.strategy.side == "BUY":
            return "SELL"
        else:  # self.strategy.side == "SELL":
            return "BUY"

    async def _futures_cancel_order(self):
        """Cancel if already an order is open corresponding to the given symbol."""
        open_orders = await helper.exchange.future.fetch_open_orders(self.strategy.symbol)
        if len(open_orders) > 0:
            for order in open_orders:
                if (
                    order["status"] == "open"
                    and order["type"] == "limit"
                    and order["side"] == self.opposite_side().lower()
                ):
                    log(f"==> Attempt to cancel order: {order}")
                    await helper.exchange.future.cancel_order(order["id"], self.strategy.symbol)
        else:
            return

    def get_btc_open_positions(self) -> int:
        btc_open_position_count = 0
        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] not in ["BTC", "BNB", "USDT"]:
                if float(balance["locked"]) > 0.0 or float(balance["free"]) > 0.0:
                    btc_open_position_count += 1

        return btc_open_position_count

    def get_exchange_future_timestamp(self):
        self.unix_timestamp_ms = helper.exchange.get_future_timestamp()
        self.current_bar_index_local = int(int((self.unix_timestamp_ms - 1) / 900))

    async def is_usdt_open(self, symbol) -> bool:
        # TODO: read from result of binance_balance.py
        future_positions = await helper.exchange.future.fetch_positions()
        self.get_exchange_future_timestamp()
        for position in future_positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                if symbol and symbol.replace("/", "") == position["symbol"].replace("/", ""):
                    return True
        return False

    async def get_usdt_open_position_count(self, is_print=False) -> int:
        """Return number of open positions."""
        count = 0
        try:
            future_positions = await helper.exchange.future.fetch_positions()
        except Exception as e:
            _colorize_traceback(e)
            await _sleep(60)
            raise e

        for position in future_positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                count += 1
                if is_print:
                    log(position, "blue")

        return count

    async def _limit(self, amount, entry_price, isolated_wallet, decimal) -> None:
        try:
            if self.opposite_side() == "SELL":
                limit_price = TP.get_long_tp(entry_price, isolated_wallet, decimal)
            else:  # opposite_side() == "BUY":
                limit_price = TP.get_short_tp(entry_price, isolated_wallet, decimal)

            quantity = abs(float(amount))
            log(f"| quantity={quantity} | limit_price={limit_price}", "bold")
            await _create_limit_order(self.strategy.symbol, quantity, limit_price, self.strategy.side)
        except TP_calculate as e:
            _colorize_traceback(e)
        except Exception as e:
            _colorize_traceback(e)
            if decimal > 0:
                await self._limit(amount, entry_price, isolated_wallet, decimal - 1)

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
        decimal = 0
        # try:
        #     output = self.mongoDB.find_key("asset", self.strategy.asset)
        #     timestamp = output["timestamp"]
        #     log(f"timestamp={timestamp} | ", end="")
        # except:
        #     pass
        log("\ntrade_price=", end="")
        for trade in enumerate(reversed(self.client.get_my_trades(symbol=self.strategy.symbol.replace("/", "")))):
            _decimal = self.get_decimal_count(trade["price"])
            if _decimal > decimal:
                decimal = _decimal

            # TODO: trade["time"] >= timestamp gerek olmayabilir
            if trade["isBuyer"]:  # and trade["time"] >= timestamp:
                quantity += float(trade["qty"])
                if quantity > asset_balance:
                    break

                log(f"{trade['price']},{trade['qty']}\n", end="")
                _sum += float(trade["qty"]) * float(trade["price"])
                contracts += float(trade["qty"])

        entry_price = _sum / contracts
        _entry_price = f"{entry_price:.{decimal}f}"
        limit_price = f"{float(_entry_price) * TP.get_profit_amount('long'):.{decimal}f}"
        log(f"quantity={asset_balance} | ", end="")
        log(f"entry={_entry_price} | ", end="")
        log(f"limit={limit_price}")
        return limit_price, _entry_price

    def spot_order_limit(self):
        log("attempting limit order for spot")
        try:
            limit_price, *_ = self.get_spot_entry()
            orders = self.client.get_open_orders(symbol=self.strategy.symbol.replace("/", ""))
            for order in orders:
                self.client.cancel_order(symbol=self.strategy.symbol.replace("/", ""), orderId=order["orderId"])

            order = self.client.order_limit_sell(
                symbol=self.strategy.symbol.replace("/", ""), price=str(limit_price), quantity=self.asset_balance()
            )
            log(order)
        except Exception as e:
            _colorize_traceback(e, is_print_exc=False)

    async def _order(self, quantity, _type="MARKET"):
        """Open futures orders in given direction."""
        try:
            # await self.bot_async.set_leverage(self.strategy.symbol, config.INITIAL_LEVERAGE)  # consumes time
            await _create_market_order(self.strategy.symbol, quantity, self.strategy.side)
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e):
                log(f"E: {e} quantity={quantity}", "red")
                decimal = self.get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening sell order with new quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return await self._order(_quantity)
                else:
                    log("E: Quantity less than zero, nothing to do.")
            else:
                raise e

    def get_future_position(self, future_positions):
        for position in future_positions:
            if abs(float(position["info"]["isolatedWallet"])) > 0.0:
                return (
                    float(position["entryPrice"]),
                    float(position["info"]["positionAmt"]),
                    abs(float(position["info"]["isolatedWallet"])),
                )

        raise Exception("E: Order related to the symbol couldn't be found.")

    async def futures_limit_order(self):
        try:
            await self._futures_cancel_order()
        except Exception as e:
            log(f"E: Cancel order: {e}")

        _amount = None
        entry_price = None
        for idx in range(10):
            try:
                if idx > 0:
                    log(f"Fetch future positions [attempt={idx + 1}]", "cyan")

                future_positions = await helper.exchange.future.fetch_positions(symbols=self.strategy.symbol)
                entry_price, _amount, isolated_wallet = self.get_future_position(future_positions)
                break
            except Exception as e:
                _colorize_traceback(e, is_print_exc=False)
                await _sleep()

        try:
            log("==> Opening a limit order: ", end="")
            log(f"entry_price={entry_price} ", "bold", end="")
            decimal = self.get_decimal_count(entry_price)
            await self._limit(_amount, entry_price, isolated_wallet, decimal)
        except Exception as e:
            _colorize_traceback(e)

    async def both_side_order(self) -> None:
        """Both side order for futures."""
        _symbol = self.strategy.symbol.replace("/USDT", "USDT")
        if await self.is_usdt_open(_symbol):
            raise Exception(f"E: Already open position for {_symbol}")

        try:
            if self.strategy.position_size == 0:
                raise Exception("E: Quantity less than zero.")

            await self._order(quantity=self.strategy.position_size)
        except Exception as e:
            _colorize_traceback(e)
            raise e

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
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
                log(f"E: {e} | quantity={quantity}")
                decimal = self.get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return self.spot_order(float(_quantity))
                else:
                    log("E: Quantity less than zero, nothing to do.")
            elif getattr(e, "message", repr(e)) == "Filter failure: MIN_NOTIONAL" and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f"==> re-opening {side} order, quantity={quantity}")
                return self.spot_order(float(quantity))
            else:
                _colorize_traceback(e)
                raise e

        return self.client.order_market(symbol=symbol.replace("/", ""), side=side, quantity=quantity)

    def get_initial_amount(self, initial_amount, _type):
        if initial_amount > 1.0:
            if _type == "BTC":
                return int(initial_amount)
            else:  # USDTPERP
                return int(round(initial_amount))
        else:
            return float(format(initial_amount, ".4f"))

    def position_size_check(self, current_price):
        """Handle order's notional must be no smaller than 5.0."""
        log(f"current_price={current_price}", "bold")
        if self.strategy.position_size >= 1.0 and self.strategy.position_size * current_price < 5.0:
            self.strategy.position_size += 1
            log(f"==> position_size_check: current_price={current_price} position_size={self.strategy.position_size}")

    async def calculate_futures_position_size(self):
        self.strategy.position_size = 0
        output = await self.symbol_price(self.strategy.symbol, "future")
        current_price = output["last"]
        if current_price == 0:
            raise Exception(f"current_price={current_price} is zero")

        if current_price < config.IGNORE_BELOW_USDT:
            raise Exception(
                f"Price of {self.strategy.symbol} is below {config.IGNORE_BELOW_USDT}$."
                f"current_price={current_price}.PASS"
            )

        if self.strategy.is_buy():
            if self.strategy.time_duration == "1m":
                initial_amount = config.INITIAL_USDT_QTY_LONG_1m / current_price
            else:
                initial_amount = config.INITIAL_USDT_QTY_LONG / current_price
        else:  # short
            if self.strategy.time_duration == "1m":
                initial_amount = config.INITIAL_USDT_QTY_SHORT_1m / current_price
            else:
                initial_amount = config.INITIAL_USDT_QTY_SHORT / current_price

        self.strategy.position_size = float(self.get_initial_amount(initial_amount, "USDT"))
        self.position_size_check(current_price)

    async def buy(self):
        if self.strategy.market == "USDTPERP":
            await self.both_side_order()
            await self.futures_limit_order()
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

    async def sell(self):
        if self.strategy.market == "USDTPERP":
            try:
                await self.both_side_order()
                await self.futures_limit_order()
            except Exception as e:
                # E: An exception of type Exception occurred. Arguments: ("E:
                # Order related to the symbol couldn't be found.",) at 3:00 AM
                _colorize_traceback(e)

    async def trade_async(self):
        try:
            if self.strategy.market == "USDTPERP":
                await self.calculate_futures_position_size()

            log(
                f"==> Opening {self.strategy.side} order in the {self.strategy.market} market for"
                f" {self.strategy.asset} {self.strategy.symbol} | size={self.strategy.position_size}"
            )
            if self.strategy.is_buy():
                await self.buy()
            elif self.strategy.is_sell():
                await self.sell()
        except Exception as e:
            log(str(e), "yellow")

    def get_decimal_count(self, value) -> int:
        try:
            return helper.exchange.future_markets[self.strategy.symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def check_on_going_positions(self):
        if self.strategy.market == "USDTPERP":
            if self.strategy.time_duration == "1m":
                if config.status["futures"]["pos_count"] >= config.USDT_MAX_POSITION_1m:
                    raise QuietExit(f"Warning: {config.USDT_MAX_POSITION} pos")
            if self.strategy.time_duration == "9m":
                if config.status["futures"]["pos_count"] >= config.USDT_MAX_POSITION:
                    raise QuietExit(f"Warning: {config.USDT_MAX_POSITION} pos")
        elif self.strategy.market == "BTC":
            if config.status["spot"]["pos_count"] >= config.SPOT_MAX_POSITION:
                raise QuietExit(f"Warning: {config.SPOT_MAX_POSITION} pos")

    async def _trade(self, strategy):
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
                with FileLock(config.status.fp_lock, timeout=1):
                    #: in case many alerts come in same minute
                    config.status["futures"]["pos_count"] += 1
            except Exception as e:
                _colorize_traceback(e)
        else:
            log("PASS")  # already open position

    async def trade(self):
        try:
            await self.trade_async()
        except Exception as e:
            log(str(e))
        finally:
            await helper.exchange.future.close()
            await helper.exchange.spot.close()

    async def trade_main(self, data_msg) -> None:
        if "alert" in data_msg:
            log(f"[{_time()}] ", end="")
            log(data_msg, "bold magenta")
            await self.discord_client.send_msg(data_msg)
            return

        self.strategy = Strategy(data_msg)
        if not hasattr(self.strategy, "position_alert_msg"):
            raise QuietExit("E: position_alert_msg is empty")

        self.pre_check()
        if "enter" not in self.strategy.position_alert_msg or self.strategy.symbol == "TEST":
            pass
        elif self.strategy.market == "BTC" and self.strategy.is_sell():
            log("Warning: Ignore BTC pair, no need to sell.")
        elif is_trade:
            await self._trade(self.strategy)

        return

    def pre_check(self) -> None:
        """Fast to read from usdt.yaml.

        It is read from the file that is updated from binance_balance.py
        """
        config.reload()
        self.check_on_going_positions()
        futures_locked_percent = config.status["futures"]["locked_per"]
        if self.strategy.time_duration != "1m":
            if futures_locked_percent > config.cfg["setup"]["STOP_LOCKED_PER"]:
                raise QuietExit(f"locked_percent={int(futures_locked_percent)}% PASS")

        if self.strategy.time_duration == "1s":
            log("===========================================", "red")
            raise QuietExit()

        free_usdt = config.status["futures"]["free"]
        if self.strategy.side == "BUY":
            if self.strategy.time_duration == "1m" and free_usdt < config.INITIAL_USDT_QTY_LONG_1m:
                raise QuietExit(f"Not enough free USDT({free_usdt}), side=BUY")

            if self.strategy.time_duration == "9m" and free_usdt < config.INITIAL_USDT_QTY_LONG:
                raise QuietExit(f"Not enough free USDT({free_usdt}), side=BUY")

        if self.strategy.side == "SELL":
            if self.strategy.time_duration == "1m" and free_usdt < config.INITIAL_USDT_QTY_SHORT_1m:
                raise QuietExit(f"Not enough free USDT({free_usdt}), side=SELL")

            if self.strategy.time_duration == "9m" and free_usdt < config.INITIAL_USDT_QTY_SHORT:
                raise QuietExit(f"Not enough free USDT({free_usdt}), side=SELL")
