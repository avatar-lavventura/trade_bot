#!/usr/bin/env python3

# TODO: convert self.client.* into async calls
from contextlib import suppress

from filelock import FileLock
from pymongo import MongoClient

from bot import helper
from bot._mongodb import Mongo
from bot.binance_balance import create_limit_order, create_market_order
from bot.bot_helper_async import TP, BotHelperAsync, TP_calculate
from bot.client_helper import DiscordClient
from bot.config import config
from bot.mongodb import Mongo
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils._log import br, log
from ebloc_broker.broker._utils.tools import _time, decimal_count, print_tb
from ebloc_broker.broker.errors import QuietExit


class Strategy:
    def __init__(self, data_msg=""):
        self.symbol: str = ""
        self.market: str = ""
        self.time_duration: str = ""
        self.size: int = 0
        self.unix_timestamp_ms: int = 0
        if "enter" in data_msg:
            log(f" * {_time()} ", end="")
            if data_msg.endswith(","):
                log(data_msg, "bold magenta", end="")
            else:
                log(f"{data_msg},", "bold magenta", end="")

        with suppress(Exception):
            self.parse_data_msg(data_msg)

        if "_abort" in data_msg:
            log(f"   ABORT {self.symbol}", "bold orange1")
            raise Exception

        if self.market in ["BTC", "BNB", "USDT", "ETH"]:
            if self.side == "SELL":
                if self.time_duration == "1s":
                    self.side = "BUY"  # BUY for 1s
                else:
                    raise QuietExit(f'E: side should be "BUY" for the {self.market} market')

        if self.time_duration == "":
            self.time_duration = config.base_time_duration

    def parse_data_msg(self, data_msg):
        self.chunks = data_msg.split(",")
        self.side_original = self.side = self.chunks[1].upper()
        self.symbol = self.chunks[0]
        if self.symbol[:-3] == "BTC":
            self.market = "BTC"
            self.asset = self.symbol[:-3]  # removes BTC at the end
            self.symbol = self.symbol.replace("BTC", "/BTC")
        else:
            if "USDTPERP" in self.symbol:
                self.market = "USDTPERP"
            elif "USDT" in self.symbol:
                self.market = "USDT"  # spot

            self.asset = self.symbol.replace(self.market, "")
            self.symbol = self.symbol.replace(self.market, "/USDT")

        self.position_alert_msg = self.chunks[2]
        msg_list = self.position_alert_msg.rsplit("_", 1)
        time_duration = msg_list[0].lower()
        if time_duration.isdigit():
            self.time_duration = f"{time_duration}m"
        else:
            if time_duration == "s":
                self.time_duration = "1s"
            else:
                self.time_duration = time_duration

        #: differs for each pair
        self.current_bar_index = self.chunks[3]
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
        except Exception as e:
            raise e

    def opposite_side(self) -> str:
        if self.strategy.is_buy():
            return "SELL"
        else:
            return "BUY"

    async def usdtperp_cancel_order(self):
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
            if balance["asset"] not in ["BTC", "BNB", "USDT", "ETH", "PAXG"]:
                if float(balance["locked"]) > 0.0 or float(balance["free"]) > 0.0:
                    btc_open_position_count += 1

        return btc_open_position_count

    def get_exchange_future_timestamp(self) -> None:
        self.unix_timestamp_ms = helper.exchange.get_future_timestamp()
        self.current_bar_index_local = int(int((self.unix_timestamp_ms - 1) / 900))

    async def is_usdt_open(self, symbol=None) -> bool:
        if not symbol:
            return False

        positions = await helper.exchange.future.fetch_positions()
        self.get_exchange_future_timestamp()
        for position in positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0 and symbol.replace("/", "") == position["symbol"].replace("/", ""):
                return True
        return False

    async def get_usdt_open_position_count(self, is_print=False) -> int:
        """Return number of open positions."""
        try:
            positions = await helper.exchange.future.fetch_positions()
        except Exception as e:
            print_tb(e)
            await _sleep(60)
            raise e

        count = 0
        for position in positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                count += 1
                if is_print:
                    log(position, "bold blue")

        return count

    async def _limit(self, amount, entry_price, isolated_wallet, decimal) -> None:
        try:
            if self.opposite_side() == "SELL":
                limit_price = TP.get_long_tp(entry_price, isolated_wallet, decimal)
            else:  # opposite_side() == "BUY":
                limit_price = TP.get_short_tp(entry_price, isolated_wallet, decimal)

            quantity = abs(float(amount))
            log(f"| limit_price={limit_price} | quantity={quantity}", "bold")
            await create_limit_order(self.strategy.symbol, quantity, limit_price, self.strategy.side)
        except TP_calculate as e:
            print_tb(e)
        except Exception as e:
            print_tb(e)
            if decimal > 0:
                await self._limit(amount, entry_price, isolated_wallet, decimal - 1)

    def asset_balance(self, asset=None) -> float:
        if not asset:
            asset = self.strategy.asset

        balances = self.client.get_account()
        for balance in balances["balances"]:
            if balance["asset"] == asset:
                return float(balance["free"]) + float(balance["locked"])

        return 0

    def get_spot_entry(self):
        asset_balance = self.asset_balance()
        _sum = 0.0
        contracts = 0.0
        quantity = 0.0
        decimal = 0
        _symbol = self.strategy.symbol.replace("/", "")
        for trade in enumerate(reversed(self.client.get_my_trades(symbol=_symbol))):
            if self.strategy.market == "USDT":
                trade = trade[1]  # spot returns trade as a tuple

            _decimal = self.get_decimal_count(trade["price"])
            if _decimal > decimal:
                decimal = _decimal

            # TODO: trade["time"] >= timestamp gerek olmayabilir
            # log(trade)
            if trade["isBuyer"]:  # and trade["time"] >= timestamp:
                quantity += float(trade["qty"])
                if quantity > asset_balance:
                    break

                _sum += float(trade["qty"]) * float(trade["price"])
                contracts += float(trade["qty"])

        entry_price = _sum / contracts
        _entry_price = f"{entry_price:.{decimal}f}"
        limit_price = f"{float(_entry_price) * TP.get_profit_amount('long'):.{decimal}f}"
        log(f"quantity={asset_balance} | entry={_entry_price} | limit={limit_price}", "bold")
        return limit_price, _entry_price

    def spot_order_limit(self):
        try:
            log("==> attempting limit order for spot ", end="")
            limit_price, *_ = self.get_spot_entry()
            _symbol = self.strategy.symbol.replace("/", "")
            orders = self.client.get_open_orders(symbol=_symbol)
            for order in orders:
                self.client.cancel_order(symbol=_symbol, orderId=order["orderId"])

            order = self.client.order_limit_sell(
                symbol=self.strategy.symbol.replace("/", ""), price=str(limit_price), quantity=self.asset_balance()
            )
            with suppress(Exception):
                del order["type"]
                del order["timeInForce"]
                del order["status"]
                del order["executedQty"]
                del order["cummulativeQuoteQty"]
                del order["orderListId"]
                del order["fills"]

            log(f"order={order}", "bold")
        except Exception as e:
            if "PRICE_FILTER" not in str(e):  # Position may close right away, not a BinanceAPIException error
                print_tb(e)

    async def _order(self, quantity, _type="MARKET"):
        """Open futures orders in given direction."""
        try:
            # await self.bot_async.set_leverage(self.strategy.symbol, 1)  # consumes time
            await create_market_order(self.strategy.symbol, quantity, self.strategy.side)
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e):
                log(f"E: {e} quantity={quantity}")
                decimal = self.get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening sell order with new quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return await self._order(_quantity)
                else:
                    if self.strategy.size >= 0.5 and self.strategy.size < 1:
                        self.strategy.size = 1

                    log("E: Quantity less than zero, nothing to do.")
            else:
                if self.strategy.size >= 0.5 and self.strategy.size < 1:
                    log("==> re-opening sell order with new quantity=1")
                    self.strategy.size = 1
                    return await self._order(self.strategy.size)

                raise e

    def get_future_position(self, positions):
        for position in positions:
            if abs(float(position["info"]["isolatedWallet"])) > 0.0:
                return (
                    float(position["entryPrice"]),
                    float(position["info"]["positionAmt"]),
                    abs(float(position["info"]["isolatedWallet"])),
                )

        raise Exception("E: Order related to the symbol couldn't be found.")

    async def futures_limit_order(self) -> None:
        try:
            await self.usdtperp_cancel_order()
        except Exception as e:
            log(f"E: cancel order: {e}")

        amount = None
        entry_price = None
        for idx in range(10):
            try:
                if idx > 0:
                    _attempt = br(f"attempt={idx + 1}")
                    log(f"Fetch future positions {_attempt}", "bold cyan")

                # at funding times like 3:00 am nearyly 16 seconds binance may hang
                positions = await helper.exchange.future.fetch_positions(symbols=self.strategy.symbol)
                entry_price, amount, isolated_wallet = self.get_future_position(positions)
                break
            except Exception as e:
                print_tb(str(e), is_print_exc=False)
                await _sleep(2)

        try:
            log("==> opening a limit order: ", end="")
            log(f"entry_price={entry_price} ", "bold", end="")
            decimal = self.get_decimal_count(entry_price)
            await self._limit(amount, entry_price, isolated_wallet, decimal)
        except Exception as e:
            print_tb(str(e))

    async def both_side_order(self) -> None:
        """Both side order for futures."""
        _symbol = self.strategy.symbol.replace("/USDT", "USDT")
        if await self.is_usdt_open(_symbol):
            raise Exception(f"E: Already open position for {_symbol}")

        try:
            if self.strategy.size == 0:
                raise Exception("E: Position size is less than zero")

            await self._order(quantity=self.strategy.size)
        except Exception as e:
            print_tb(str(e))
            raise e

    def spot_order(self, quantity: float, symbol=None, side=None):
        if symbol:
            self.strategy.symbol = symbol

        if side:
            self.strategy.side = side

        try:
            log(f"order_quantity={quantity}", "bold")
            if not symbol:
                symbol = self.strategy.symbol

            if not side:
                side = self.strategy.side

            order = self.client.order_market(symbol=symbol.replace("/", ""), side=side, quantity=quantity)
            #: creates new item or overwrites on it
            config.timestamp["spot_timestamp"][self.strategy.asset] = order["transactTime"]
            with suppress(Exception):
                del order["timeInForce"]
                del order["orderListId"]
                del order["price"]
                del order["status"]
                del order["type"]
                del order["origQty"]
                del order["executedQty"]

            try:
                config.log["root"][self.strategy.asset] += 1
            except:
                config.log["root"][self.strategy.asset] = 1

            return order
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
                log(f"E: {e}")
                decimal = self.get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                if quantity == float(_quantity):
                    if float(_quantity) >= 0.5 and float(_quantity) < 1:
                        _quantity = "1"
                    else:
                        if "Filter failure: LOT_SIZE" in str(e):
                            log(str(e))
                        else:
                            print_tb(e)

                        raise e

                log(f"==> re-opening {side} order | ", end="")
                if float(_quantity) > 0:
                    return self.spot_order(float(_quantity))
                else:
                    log("E: Quantity less than or equal to zero, nothing to do")
            elif "Filter failure: MIN_NOTIONAL" in str(e) and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f"==> re-opening {side} order | ", end="")
                return self.spot_order(float(quantity))
            else:
                if "Filter failure: LOT_SIZE" in str(e):
                    log(str(e))
                else:
                    print_tb(e)

                raise e

    def get_initial_amount(self, initial_amount, _type):
        if initial_amount > 1.0:
            if _type == "BTC":
                return int(initial_amount)
            else:  # usdtperp
                return int(round(initial_amount))
        else:
            return float(format(initial_amount, ".4f"))

    def futues_size_check(self, last_price, size=5.0):
        """Handle order's notional must be no smaller than 5 USDT."""
        log(f"p={last_price}", "bold")
        if self.strategy.size >= 1.0 and self.strategy.size * last_price < size:
            self.strategy.size += 1
            log(f"==> size_check: last_price={last_price} size={self.strategy.size}", "bold")

    def ignore_below_usdtperp(self, last_price):
        ignore_limit_usdt = 0.01
        if last_price < ignore_limit_usdt:
            raise Exception(f"{self.strategy.symbol} price<{ignore_limit_usdt}$, last_price={last_price}, PASS", "bold")

    async def calculate_futures_size(self):
        self.strategy.size = 0
        output = await self.symbol_price(self.strategy.symbol, "future")
        last_price = output["last"]
        if last_price == 0:
            raise Exception("E: last_price is zero")

        # ignore_below_usdtperp(last_price)
        if self.strategy.is_buy():
            if self.strategy.time_duration == "1m":
                initial_amount = config.initial_usdt_qty_long["1m"] / last_price
            else:
                initial_amount = config._initial_usdt_qty_long / last_price
        else:  # short
            if self.strategy.time_duration == "1m":
                initial_amount = config.initial_usdt_qty_short["1m"] / last_price
            else:
                initial_amount = config._initial_usdt_qty_short / last_price

        self.strategy.size = float(self.get_initial_amount(initial_amount, "USDT"))
        self.futues_size_check(last_price)

    async def buy(self):
        if self.strategy.market == "USDTPERP":
            await self.both_side_order()
            await self.futures_limit_order()
        elif self.strategy.market == "BTC":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            last_price = output["last"]
            try:
                initial_amount = config.initial_btc_quantity / last_price
                self.strategy.size = self.get_initial_amount(initial_amount, "BTC")
                decimal = self.get_decimal_count(self.strategy.size)
                self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
                order = self.spot_order(float(self.strategy.size))
                log(order, "bold")
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
        elif self.strategy.market == "USDT":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            last_price = output["last"]
            try:
                # if self.strategy.asset in ["BTG"]:  # consider assets minumum buy is >= 50
                #     initial_amount = 100 / last_price
                # if self.strategy.side_original == "SELL":  # could be riskly less position size is opened
                #     initial_amount = config.cfg["root"]["usdt"]["1s_alert"]["sell"] / last_price
                # else:
                initial_amount = config.cfg["root"]["usdt"]["pos"]["base"] / last_price
                self.strategy.size = self.get_initial_amount(initial_amount, "USDT")
                decimal = self.get_decimal_count(self.strategy.size)
                self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
                if float(self.strategy.size) == 0.0:
                    self.strategy.size = 0.1

                log(self.spot_order(float(self.strategy.size)))
                if self.strategy.asset not in config.SPOT_IGNORE_LIST:
                    self.spot_order_limit()
            except Exception as e:
                print_tb(e)
                raise e

    async def sell(self):
        if self.strategy.market == "USDTPERP":
            try:
                await self.both_side_order()
                await self.futures_limit_order()
            except Exception as e:
                # Exception: Order related to the symbol couldn't be found at 3:00 AM"
                print_tb(e)

    async def trade_async(self):
        try:
            if self.strategy.market == "USDTPERP":
                await self.calculate_futures_size()
            else:
                output = await self.symbol_price(self.strategy.symbol, "spot")
                log(f"last_price={output['last']}", "bold")

            if self.strategy.side == "BUY":
                side_color = "green"
            else:
                side_color = "red"

            log(
                f"==> opening [{side_color}]{self.strategy.side}[/{side_color}] order in the "
                f"[blue]{self.strategy.market}[/blue] market for [blue]{self.strategy.asset}[/blue]"
                f" {self.strategy.symbol} ",
                end="",
            )
            if self.strategy.size != 0:
                log(f"| size={self.strategy.size}", "bold")

            if self.strategy.is_buy():
                await self.buy()
            elif self.strategy.is_sell():
                await self.sell()
        except Exception as e:
            log(str(e), "bold yellow")

    def get_decimal_count(self, value) -> int:
        try:
            if self.strategy.market == "USDTPERP":
                return helper.exchange.future_markets[self.strategy.symbol]["precision"]["price"]
            else:  # elif self.strategy.market in ["BTC", "USDT"]:
                return helper.exchange.spot_markets[self.strategy.symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def check_on_going_positions(self):
        if self.strategy.market == "USDTPERP":
            if self.strategy.time_duration == "":
                self.strategy.time_duration = "9m"

            pos_count = config.USDTPERP_MAX_POSITION[self.strategy.time_duration]
            if config.status["futures"]["pos_count"] >= pos_count:
                raise QuietExit(f"Warning: {pos_count} pos")
        elif self.strategy.market == "BTC":
            if config.status["spot"]["pos_count"] >= config.SPOT_MAX_POSITION:
                raise QuietExit(f"Warning: {config.SPOT_MAX_POSITION} pos")
        elif self.strategy.market == "USDT":
            if self.strategy.asset in config.white_list:
                if config.status["spot"]["pos_count"] >= config.SPOT_MAX_POSITION + 1:
                    raise QuietExit(f"warning: {config.SPOT_MAX_POSITION + 1} pos")
            else:
                if config.status["spot"]["pos_count"] >= config.SPOT_MAX_POSITION:
                    raise QuietExit(f"warning: {config.SPOT_MAX_POSITION} pos")

    async def _trade(self):
        is_open = False
        if self.strategy.market == "USDTPERP":
            is_open = await self.is_usdt_open(self.strategy.symbol)
        elif self.strategy.market in ["BTC", "USDT"]:
            balances = self.client.get_account()
            for balance in balances["balances"]:
                if balance["asset"] == self.strategy.asset and float(balance["locked"]) > 0.0:
                    is_open = True
                    break

        if not is_open:
            try:
                await self.trade_async()
                with FileLock(config.status.fp_lock, timeout=1):
                    #: in case many alerts come in same minute
                    if self.strategy.market == "USDTPERP":
                        config.status["futures"]["pos_count"] += 1
                    elif self.strategy.market == "USDT":
                        config.status["spot"]["pos_count"] += 1
            except Exception as e:
                print_tb(e)
        else:
            log("PASS", "bold")  # already open position

    async def trade(self) -> None:
        try:
            await self.trade_async()
        except Exception as e:
            log(str(e))
        finally:
            await helper.exchange.future.close()
            await helper.exchange.spot.close()

    async def trade_main(self, data_msg) -> None:
        if "alert" in data_msg:
            if "abort" in data_msg:
                log(f"   ABORT {data_msg}", "bold orange1")
            elif "_bist" in data_msg:
                await self.discord_client.send_msg(data_msg, "bist_alpy")
            else:
                log(f" * {_time()} [bold magenta]{data_msg}")
                await self.discord_client.send_msg(data_msg, "alpy")

            return

        self.strategy = Strategy(data_msg)
        if not hasattr(self.strategy, "position_alert_msg"):
            raise QuietExit("E: position_alert_msg is empty")

        self.pre_check()
        if "enter" not in self.strategy.position_alert_msg or self.strategy.symbol == "TEST":
            return
        elif self.strategy.market == "BTC" and self.strategy.is_sell():
            log("warning: Ignore BTC pair, no need to sell.")

        await self._trade()

    def pre_check(self) -> None:
        """Faster to read from usdt.yaml.

        It is read from the file that is updated from binance_balance.py
        """
        config.reload()
        self.check_on_going_positions()
        # futures_locked_percent = config.status["futures"]["locked_per"]
        # if self.strategy.time_duration != "1m":
        #     if futures_locked_percent > config.cfg["root"]["usdtperp"]["stop_locked_per"]:
        #         raise QuietExit(f"locked_percent={int(futures_locked_percent)}% PASS")

        free_usdt = config.status["root"]["free_usdt"]
        duration = self.strategy.time_duration
        raise_msg = f"not enough free usdt({free_usdt}),side={self.strategy.side}"
        if self.strategy.side == "BUY":
            if duration == "1m" and free_usdt < config.initial_usdt_qty_long[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_usdt < config._initial_usdt_qty_long:
                raise QuietExit(raise_msg)

        if self.strategy.side == "SELL":
            if duration == "1m" and free_usdt < config.initial_usdt_qty_short[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_usdt < config._initial_usdt_qty_short:
                raise QuietExit(raise_msg)
