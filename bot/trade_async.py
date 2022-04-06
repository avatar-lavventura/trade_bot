#!/usr/bin/env python3

from broker._utils._async import _sleep
from broker._utils._log import br, log
from broker._utils.tools import _date, decimal_count, print_tb
from broker.errors import QuietExit
from contextlib import suppress
from filelock import FileLock
from pymongo import MongoClient

from bot import helper
from bot.bot_helper_async import TP, BotHelperAsync, TP_calculate
from bot.client_helper import DiscordClient
from bot.config import config
from bot.mongodb import Mongo
from bot.spot_lib import create_limit_order, create_market_order


class Strategy:
    def __init__(self, data_msg=""):
        self.exchange = None
        self.side: str = ""
        self.symbol: str = ""
        self.market: str = ""
        self.time_duration: str = ""
        self.size: int = 0
        self.unix_timestamp_ms: int = 0
        if "enter" in data_msg:
            log(f" * {_date()} ", end="")
            log(data_msg, "bold magenta", end="")
            if not data_msg.endswith(","):
                log(",", "bold magenta", end="")

        try:
            self.parse_data_msg(data_msg)
        except QuietExit as e:
            raise e
        except Exception:
            pass

        if "_abort" in data_msg:
            log(f"   ABORT {self.symbol}", "bold orange1", is_write=False)
            raise Exception

    def parse_data_msg(self, data_msg) -> None:
        self.chunks = data_msg.split(",")
        self.side_original = self.side = self.chunks[1].upper()
        self.symbol = self.chunks[0]
        if self.symbol[-3:] == "BTC":
            self.market = "BTC"
            self.asset = self.symbol[:-3]  # removes BTC at the end
            self.symbol = f"{self.asset}/BTC"
            self.exchange = helper.exchange.spot_btc
        else:
            if "USDTPERP" in self.symbol:
                self.market = "USDTPERP"
            elif "USDT" in self.symbol:
                self.market = "USDT"  # spot
                self.exchange = helper.exchange.spot_usdt

            self.asset = self.symbol[: -len(self.market)]  # removes USDT* at the end
            self.symbol = f"{self.asset}/USDT"

        if self.asset in config.SPOT_IGNORE_LIST:
            raise QuietExit("ignore_list PASS")

        self.position_alert_msg = self.chunks[2]
        msg_list = self.position_alert_msg.rsplit("_", 1)
        time_duration = msg_list[0].lower()
        if time_duration.isdigit():
            self.time_duration = f"{time_duration}m"
        elif time_duration == "s":
            self.time_duration = "1s"
        else:
            self.time_duration = time_duration

        self.current_bar_index = self.chunks[3]  # differs for each pair
        self.time = self.chunks[4]

    def is_buy(self) -> bool:
        return self.side == "BUY"

    def is_sell(self) -> bool:
        return self.side == "SELL"


class BotHelper:
    def __init__(self, discord_client=None) -> None:
        mc = MongoClient()
        self.mongoDB = Mongo(mc, mc["trader_bot"]["order"])
        self.unix_timestamp_ms: int = 0
        self.current_bar_index_local: int = 0
        self.strategy = Strategy()
        self.bot_async = BotHelperAsync()
        if discord_client:
            self.discord_client: "DiscordClient" = discord_client

    async def symbol_price(self, symbol, _type):
        try:
            if _type == "future:":
                return await helper.exchange.future.fetch_ticker(symbol)
            else:
                return await self.strategy.exchange.fetch_ticker(symbol)
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
        if len(open_orders):
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
            if initial_margin > 0 and symbol.replace("/", "") == position["symbol"].replace("/", ""):
                return True

        return False

    async def get_futures_open_position_count(self, is_print=False) -> int:
        """Return number of open positions."""
        try:
            positions = await helper.exchange.future.fetch_positions()
        except Exception as e:
            print_tb(e)
            raise e

        count = 0
        for position in positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0:
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

    async def asset_balance(self, asset=None) -> float:
        if not asset:
            asset = self.strategy.asset

        try:
            balances = await self.strategy.exchange.fetch_balance()
        except Exception as e:
            raise e

        for balance in balances["info"]["balances"]:
            if balance["asset"] == asset:
                return float(balance["free"]) + float(balance["locked"])

        return 0

    async def get_spot_entry(self):
        asset_balance = await self.asset_balance()
        _sum = 0
        contracts = 0
        quantity = 0
        decimal = 0
        symbol = self.strategy.symbol.replace("/", "")
        trades = await self.strategy.exchange.fetch_my_trades(symbol=symbol, limit=10)
        for trade in reversed(trades):
            trade = trade["info"]
            _decimal = self.get_decimal_count(trade["price"])
            if _decimal > decimal:
                decimal = _decimal

            if trade["isBuyer"]:
                quantity += float(trade["qty"])
                if quantity > asset_balance:
                    break

                _sum += float(trade["qty"]) * float(trade["price"])
                contracts += float(trade["qty"])

        if contracts == 0:
            # it may end up fill the order right away
            raise QuietExit(f"warning: {symbol} amount is zero")

        entry_price = _sum / contracts
        entry_price = f"{entry_price:.{decimal}f}"
        limit_price = f"{float(entry_price) * TP.get_profit_amount():.{decimal}f}"
        log(f"quantity={asset_balance} | entry={entry_price} | limit={limit_price}", "bold")
        return limit_price, entry_price

    async def spot_order_limit(self):
        try:
            log("==> attempting limit order for spot ", end="")
            limit_price, *_ = await self.get_spot_entry()
            symbol = self.strategy.symbol.replace("/", "")
            open_orders = await self.strategy.exchange.fetch_open_orders(symbol=symbol)
            for order in open_orders:
                await self.strategy.exchange.cancel_order(order["info"]["orderId"], symbol)

            asset_balance = await self.asset_balance()
            order = await self.strategy.exchange.create_limit_sell_order(symbol, asset_balance, limit_price)
            order = order["info"]
            with suppress(Exception):
                del order["type"]
                del order["timeInForce"]
                del order["status"]
                del order["executedQty"]
                del order["cummulativeQuoteQty"]
                del order["orderListId"]
                del order["fills"]

            log(f"order={order}", "bold")
        except QuietExit as e:
            raise e
        except Exception as e:
            if "PRICE_FILTER" not in str(e):
                # position may close right away, not a BinanceAPIException error
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
                if float(_quantity) > 0:
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
        for pos in positions:
            if abs(float(pos["info"]["isolatedWallet"])) > 0:
                return (
                    float(pos["entryPrice"]),
                    float(pos["info"]["positionAmt"]),
                    abs(float(pos["info"]["isolatedWallet"])),
                )

        raise Exception("order related to the symbol couldn't be found")

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
        symbol = self.strategy.symbol.replace("/USDT", "USDT")
        if await self.is_usdt_open(symbol):
            raise Exception(f"already open position for {symbol}")

        try:
            if self.strategy.size == 0:
                raise Exception("position size is less than zero")

            await self._order(quantity=self.strategy.size)
        except Exception as e:
            print_tb(str(e))
            raise e

    async def spot_order(self, quantity: float, symbol=None, side=None):
        log(f"order_quantity={quantity}", "bold")
        if symbol:
            self.strategy.symbol = symbol
        else:
            symbol = self.strategy.symbol

        if side:
            self.strategy.side = side
        else:
            side = self.strategy.side

        try:
            order = await self.strategy.exchange.create_market_buy_order(symbol, quantity)
            order = order["info"]
            #: creates new item or overwrites on it
            config.timestamp[f"{self.strategy.market.lower()}_timestamp"][self.strategy.asset] = int(
                order["transactTime"]
            )
            with suppress(Exception):
                del order["timeInForce"]
                del order["orderListId"]
                del order["price"]
                del order["status"]
                del order["type"]
                del order["origQty"]
                del order["executedQty"]

            if self.strategy.asset in config.env[self.strategy.market.lower()].hit:
                config.env[self.strategy.market.lower()].hit[self.strategy.asset] += 1
            else:
                config.env[self.strategy.market.lower()].hit[self.strategy.asset] = 1

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
                if self.strategy.market.lower() == "usdt" and config.env["usdt"].status["free"] < 15:
                    raise QuietExit("Not enough balance") from None

                if self.strategy.market.lower() == "btc" and float(config.env["btc"].status["free"]) < 0.0003:
                    raise QuietExit("Not enough balance") from None

                if float(_quantity) > 0:
                    return await self.spot_order(float(_quantity))
                else:
                    log("E: Quantity less than or equal to zero, nothing to do")
            elif "Filter failure: MIN_NOTIONAL" in str(e) and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f"==> re-opening {side} order | ", end="")
                return await self.spot_order(float(quantity))
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

    async def calculate_futures_size(self):
        self.strategy.size = 0
        output = await self.symbol_price(self.strategy.symbol, "future")
        last_price = output["last"]
        if last_price == 0:
            raise Exception("last_price is zero")

        if self.strategy.is_buy():
            if self.strategy.time_duration == "1m":
                initial_amount = config.initial_usdt_qty_long["1m"] / last_price
            else:
                initial_amount = config._initial_usdt_qty / last_price
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
            return

        if self.strategy.market == "BTC":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            initial_amount = config.initial_btc_quantity / output["last"]
            self.strategy.size = self.get_initial_amount(initial_amount, "BTC")
            decimal = self.get_decimal_count(self.strategy.size)
            self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
        elif self.strategy.market == "USDT":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            last_price = output["last"]
            initial_amount = config.cfg["root"]["usdt"]["initial"] / last_price
            self.strategy.size = self.get_initial_amount(initial_amount, "USDT")
            decimal = self.get_decimal_count(self.strategy.size)
            self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
            if float(self.strategy.size) == 0:
                self.strategy.size = 0.1
                amount = last_price * self.strategy.size
                if last_price * self.strategy.size > 20:
                    log(f"E: order_amount={round(amount)} PASS")
                    return

        log(await self.spot_order(float(self.strategy.size)))
        try:
            config.env[self.strategy.market.lower()].stats[_date(_type="month")] += 1
        except:
            config.env[self.strategy.market.lower()].stats[_date(_type="month")] = 1

        if self.strategy.asset not in config.SPOT_IGNORE_LIST:
            await self.spot_order_limit()

    async def sell(self):
        if self.strategy.market == "USDTPERP":
            try:
                await self.both_side_order()
                await self.futures_limit_order()
            except Exception as e:
                print_tb(e)  # order related to the symbol couldn't be found at 3:00 AM"

    async def trade_async(self):
        try:
            if self.strategy.market == "USDTPERP":
                await self.calculate_futures_size()
            else:
                output = await self.symbol_price(self.strategy.symbol, "spot")
                log(f"last_price={output['last']}", "bold")

            side_color = "green" if self.strategy.side == "BUY" else "red"
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

            # for btc and usdt spot market
            return helper.exchange.spot_markets[self.strategy.symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def check_on_going_positions(self) -> None:
        if self.strategy.market == "USDTPERP":
            pos_count = config.USDTPERP_MAX_POSITION[self.strategy.time_duration]
            if config.status_usdtperp["count"] >= pos_count:
                raise QuietExit(f"warning: {pos_count} pos")
        elif self.strategy.market == "BTC":
            if config.status_btc["count"] >= config.BTC_MAX_POSITION:
                raise QuietExit(f"warning: {config.BTC_MAX_POSITION} pos")
        elif self.strategy.market == "USDT":
            if self.strategy.asset in config.white_list:
                if config.status_usdt["count"] >= config.USDT_MAX_POSITION + 1:
                    raise QuietExit(f"warning: {config.USDT_MAX_POSITION + 1} pos")
            else:
                if config.status_usdt["count"] >= config.USDT_MAX_POSITION:
                    raise QuietExit(f"warning: {config.USDT_MAX_POSITION} pos")

    async def _fetch_balance(self):
        for _ in range(5):
            with suppress(Exception):
                return await self.strategy.exchange.fetch_balance()

        raise Exception("timestamp error")

    async def _trade(self):
        if self.strategy.market.lower() == "usdt" and config.env["usdt"].status["free"] < 15:
            raise QuietExit("Not enough balance")

        if self.strategy.market.lower() == "btc" and float(config.env["btc"].status["free"]) < 0.0003:
            raise QuietExit("Not enough balance")

        is_open = False
        if self.strategy.market == "USDTPERP":
            is_open = await self.is_usdt_open(self.strategy.symbol)
        elif self.strategy.market in ["BTC", "USDT"]:
            balances = await self._fetch_balance()
            for balance in balances["info"]["balances"]:
                if balance["asset"] == self.strategy.asset and float(balance["locked"]) > 0:
                    is_open = True
                    break

        if not is_open:
            try:
                await self.trade_async()
                with FileLock(config.status.fp_lock, timeout=5):
                    #: in case many alerts come in same minute
                    if self.strategy.market.lower() == "usdtperp":
                        config.status_usdtperp["count"] += 1
                    elif self.strategy.market.lower() == "usdt":
                        config.status_usdt["count"] += 1
                    elif self.strategy.market.lower() == "btc":
                        config.status_btc["count"] += 1
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
            await helper.exchange.spot_usdt.close()
            await helper.exchange.spot_btc.close()

    def pre_check(self) -> None:
        """Check count of open positions.

        Faster to read from status.yaml file. Positions counts are read from
        the yaml file that is updated from binance_balance.py.
        """
        config.reload()
        self.check_on_going_positions()
        free_balance = config.env[self.strategy.market.lower()].status["free"]
        raise_msg = f"not enough free usdt({free_balance}),side={self.strategy.side}"
        if self.strategy.market.lower() == "usdt" and free_balance < 15.0:
            raise QuietExit(raise_msg)

        # self.pre_check_usdtperp(free_balance, raise_msg)

    def pre_check_usdtperp(self, free_balance, raise_msg) -> None:
        # futures_locked_percent = config.status["futures"]["locked_per"]
        # if self.strategy.time_duration != "1m":
        #     if futures_locked_percent > config.cfg["root"]["usdtperp"]["stop_locked_per"]:
        #         raise QuietExit(f"locked_percent={int(futures_locked_percent)}% PASS")
        duration = self.strategy.time_duration
        if self.strategy.side == "BUY":
            if duration == "1m" and free_balance < config.initial_usdt_qty_long[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_balance < config._initial_usdt_qty:
                raise QuietExit(raise_msg)

        if self.strategy.side == "SELL":
            if free_balance < config.initial_usdt_qty_short[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_balance < config._initial_usdt_qty_short:
                raise QuietExit(raise_msg)

    async def trade_main(self, data_msg) -> None:
        if "alert" in data_msg:
            if "abort" in data_msg:
                log(f"   ABORT {data_msg}", "bold orange1")
            elif "_bist" in data_msg:
                await self.discord_client.send_msg(data_msg, "bist_alpy")
            else:
                log(f" * {_date()} [bold magenta]{data_msg}")
                await self.discord_client.send_msg(data_msg, "alpy")

            return

        self.strategy = Strategy(data_msg)
        if not hasattr(self.strategy, "position_alert_msg"):
            raise QuietExit("E: position_alert_msg is empty")

        self.pre_check()  # TODO SLOW FIND ALTERNATIVE FASTER SOLUTION
        if "enter" not in self.strategy.position_alert_msg:
            return
        elif self.strategy.market == "BTC" and self.strategy.is_sell():
            log("warning: ignore BTC pair, no need to sell.")

        await self._trade()
