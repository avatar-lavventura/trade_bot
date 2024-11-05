#!/usr/bin/env python3

import time
from contextlib import suppress

from _utils._log import log
from _utils.tools import _date, decimal_count, print_tb
from errors import QuietExit
from pymongo import MongoClient

from bot import cfg
from bot import config as helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.client_helper import DiscordClient
from bot.config import config
from bot.mongodb import Mongo
from bot.spot_lib import create_limit_order, create_market_order
from bot.take_profit import TP_calculate


class Strategy:
    def __init__(self, data_msg=""):
        self.exchange = None
        self.side: str = ""
        self.symbol: str = ""
        self.market: str = ""
        self.time_duration: str = ""
        self.size: float = 0
        self.unix_timestamp_ms: int = 0
        if "enter" in data_msg:
            log(f"* {_date(_format='%m-%d %H:%M:%S')} ", end="")
            if ", (" in data_msg:
                data_msg = data_msg.split(", (", 1)[0]

            if "USDT" in data_msg:
                c = "blue"
            else:
                c = "magenta"

            log(data_msg, c, h=False, end="")
            if not data_msg.endswith(","):
                log(",", c, h=False, end="")

        try:
            self.parse_msg(data_msg)
        except QuietExit as e:
            raise e
        except Exception:
            pass

        if "_abort" in data_msg:
            log(f" ABORT {self.symbol}", "bold orange1", is_write=False)
            raise Exception

    def parse_msg(self, data_msg) -> None:
        self.chunks = data_msg.split(",")
        self.side_original = self.side = self.chunks[1].upper()
        self.symbol = self.chunks[0]
        if self.symbol[-3:] == "BTC":
            self.market = "BTC"
            self.asset = self.symbol[:-3]  # removes BTC at the end
            self.symbol = f"{self.asset}/BTC"
            self.exchange = helper.exchange.spot_btc
        else:
            if "USDT" in self.symbol or "USDTPERP" in self.symbol:
                self.market = "USDT"  # spot
                self.exchange = helper.exchange.spot_usdt
                self.asset = self.symbol[: -len(self.market)]  # removes "USDT" at the end
                self.symbol = f"{self.asset}/USDT"
            elif "BUSD" in self.symbol:
                self.market = "BUSD"  # spot
                self.exchange = helper.exchange.spot_usdt
                self.asset = self.symbol[: -len(self.market)]  # removes "BUSD" at the end
                self.symbol = f"{self.asset}/BUSD"

        if (
            self.asset in config.SPOT_IGNORE_LIST
            or self.asset in config.cfg["root"][self.market.lower()]["entry_prices"]
        ):
            raise QuietExit("ignore list pass")

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
        self.bot_async = BotHelperAsync()
        self.strategy = Strategy()
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

    async def _limit(self, amount, entry_price, isolated_wallet, decimal) -> None:
        try:
            if self.opposite_side() == "SELL":
                limit_price = TP.get_long_tp(entry_price, isolated_wallet, decimal)
            else:
                limit_price = TP.get_short_tp(entry_price, isolated_wallet, decimal)

            quantity = abs(float(amount))
            log(f"| limit_price={limit_price} | qty={quantity}")
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
        log(f"qty={asset_balance} entry={entry_price} limit={limit_price}")
        return limit_price, entry_price

    async def spot_order_limit(self):
        try:
            log("==> attempting limit order ", end="")
            limit_price, *_ = await self.get_spot_entry()
            symbol = self.strategy.symbol.replace("/", "")
            open_orders = await self.strategy.exchange.fetch_open_orders(symbol=symbol)
            for order in open_orders:
                await self.strategy.exchange.cancel_order(order["info"]["orderId"], symbol)

            asset_balance = await self.asset_balance()
            order = await self.strategy.exchange.create_limit_sell_order(symbol, asset_balance, limit_price)
            order = order["info"]
            for item in cfg.order_del_list:
                with suppress(Exception):
                    del order[item]

            with suppress(Exception):
                if not order["fills"]:
                    del order["fills"]

                if float(order["cummulativeQuoteQty"]) == 0:
                    del order["cummulativeQuoteQty"]

            log(f"order={order}")
        except QuietExit as e:
            raise e
        except Exception as e:
            if "PRICE_FILTER" not in str(e):
                # position may close right away, not a BinanceAPIException error
                print_tb(e)

    async def spot_order(self, quantity: float, symbol=None, side=None):
        log(f"order_qty={quantity}")
        _type = self.strategy.market.lower()
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
            config.env[_type].timestamps["root"][self.strategy.asset] = int(order["transactTime"])
            config.env[_type].hit._inc(self.strategy.asset)
            for item in cfg.order_del_list:
                with suppress(Exception):
                    del order[item]

            with suppress(Exception):
                for item in order["fills"]:
                    del item["qty"]
                    del item["commission"]
                    del item["commissionAsset"]
                    del item["tradeId"]
                    del item["price"]

            order["fills"] = order["fills"][0]
            return order
        except Exception as e:
            if "insufficient balance" in str(e) or "InsufficientFunds" in str(e):
                log(str(e).lower())
            elif "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(
                e
            ):
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
                if float(config.env[_type].status["free"]) < config.cfg["root"][_type]["initial"]:
                    raise QuietExit("not enough balance") from None

                if float(_quantity) > 0:
                    return await self.spot_order(float(_quantity))
                else:
                    log("E: Quantity less than or equal to zero, nothing to do")
            elif ("Filter failure: MIN_NOTIONAL" in str(e) or "Filter failure: NOTIONAL" in str(e)) and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f" *  re-opening [green]{side}[/green] ", end="")
                return await self.spot_order(float(quantity))
            elif ("Filter failure: MIN_NOTIONAL" in str(e) or "Invalid quantity" in str(e)) and quantity < 1:
                quantity = 1
                log(f" *  re-opening [green]{side}[/green] ", end="")
                return await self.spot_order(float(quantity))
            else:
                if "Filter failure: LOT_SIZE" in str(e):
                    log(str(e).lower())
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

    def futues_size_check(self, last_price, size=5.0) -> None:
        """Handle order's notional must be no smaller than 5 USDT."""
        log(f"p={last_price}")
        if self.strategy.size >= 1.0 and self.strategy.size * last_price < size:
            self.strategy.size += 1
            log(f"==> size_check: last_price={last_price} size={self.strategy.size}")

    async def buy(self):
        if self.strategy.market == "BTC":
            output = await self.symbol_price(self.strategy.symbol, "spot")
            initial_amount = config.initial_btc_quantity / output["last"]
            self.strategy.size = self.get_initial_amount(initial_amount, "BTC")
            decimal = self.get_decimal_count(self.strategy.size)
            self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
        elif self.strategy.market in ["USDT", "BUSD"]:
            output = await self.symbol_price(self.strategy.symbol, "spot")
            last_price = output["last"]
            if self.strategy.symbol == "STRK/USDT":
                _initial = 10.4
                initial_amount = _initial / last_price
            else:
                initial_amount = config.cfg["root"]["usdt"]["initial"] / last_price

            self.strategy.size = self.get_initial_amount(initial_amount, self.strategy.market)
            if self.strategy.symbol != "STRK/USDT":
                decimal = self.get_decimal_count(self.strategy.size)
                self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"
                if 0 < float(self.strategy.size) < 10 and float(self.strategy.size) * last_price < 10:
                    self.strategy.size = float(self.strategy.size) + 1
                    self.strategy.size = f"{float(self.strategy.size):.{decimal}f}"

            if float(self.strategy.size) == 0:
                self.strategy.size = 0.1
                amount = last_price * self.strategy.size
                if last_price * self.strategy.size > 20:
                    log(f"E: order_amount={round(amount)} pass")
                    return

        log(await self.spot_order(float(self.strategy.size)))
        config.env[self.strategy.market.lower()].stats._inc(_date(_type="year"))
        if self.strategy.asset not in config.SPOT_IGNORE_LIST:
            await self.spot_order_limit()

    async def trade_async(self):
        try:
            if self.strategy.market == "USDTPERP":
                await self.calculate_futures_size()

            side_color = "green" if self.strategy.side == "BUY" else "red"
            log(
                f"==> opening [{side_color}]{self.strategy.side}[/{side_color}] order in the "
                f"[blue]{self.strategy.market}[/blue] market for [blue]{self.strategy.asset}[/blue] "
                f"symbol={self.strategy.symbol} ",
                end="",
            )
            if self.strategy.size != 0:
                log(f"| size={self.strategy.size}")

            if self.strategy.is_buy():
                await self.buy()
            elif self.strategy.is_sell():
                await self.sell()

            time.sleep(0.2)  # helps to wait belence show up for the limit order
        except Exception as e:
            print_tb(e)  # DELETEME
            if e:
                log(f"E: {e}")

    def get_decimal_count(self, value) -> int:
        try:
            # if self.strategy.market == "USDTPERP":
            #     return helper.exchange.future_markets[self.strategy.symbol]["precision"]["price"]

            # for btc and usdt spot market
            return helper.exchange.spot_markets[self.strategy.symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def check_on_going_positions(self) -> None:
        pos_count = config.env[self.strategy.market.lower()]._status.find_one("count")["value"]
        defined_pos_count = config.env[self.strategy.market.lower()].max_pos
        if self.strategy.symbol == "PAXG/USDT":
            pass
        elif pos_count >= defined_pos_count:
            raise QuietExit(f"warning: {defined_pos_count} pos")

    async def _fetch_balance(self):
        for _ in range(5):
            try:
                return await self.strategy.exchange.fetch_balance()
            except:
                time.sleep(2)

        raise Exception("timestamp error")

    async def _trade(self):
        self.pre_check()
        if (
            self.strategy.market.lower() == "usdt"
            and config.env["usdt"].status["free"] < config.cfg["root"]["usdt"]["initial"]
        ) or (
            self.strategy.market.lower() == "btc"
            and float(config.env["btc"].status["free"]) < config.cfg["root"]["btc"]["initial"]
        ):
            raise QuietExit("not enough balance")

        is_open = False
        if self.strategy.market.lower() in ["btc", "usdt", "busd"]:
            balances = await self._fetch_balance()
            for balance in balances["info"]["balances"]:
                if balance["asset"] == self.strategy.asset and float(balance["locked"]) > 0:
                    is_open = True
                    log("pass")
                    break

        if not is_open:
            log()

        if not is_open:
            try:
                await self.trade_async()
                config.env[self.strategy.market.lower()]._status._inc("count")
            except Exception as e:
                print_tb(e)

    async def trade(self) -> None:
        try:
            await self.trade_async()
        except Exception as e:
            log(str(e))
        finally:
            await helper.exchange.spot_usdt.close()
            await helper.exchange.spot_btc.close()
            await helper.exchange.future.close()

    def pre_check(self) -> None:
        """Check count of open positions.

        Faster to read from status.yaml file. Positions counts are read from
        the yaml file that is updated from binance_balance.py.
        """
        config._reload()  # TODO could be *SLOW* learn its run-time
        initial = config.cfg["root"]["usdt"]["initial"]
        self.check_on_going_positions()
        free_balance = config.env[self.strategy.market.lower()].status["free"]
        if self.strategy.market.lower() == "usdt" and free_balance < initial:
            raise QuietExit(f"not enough USDT([cy]${round(free_balance)}[/cy]) for [cy]${initial}")

    async def bist_discord_send_msg(self, symbol, side) -> None:
        if side == "buy":
            await self.discord_client.send_msg(f"```diff\n+{symbol} {side.upper()}\n```", "bist")
        else:
            await self.discord_client.send_msg(f"```diff\n-{symbol} {side.upper()}\n```", "bist")

    async def trade_main(self, data_msg) -> None:
        if "alert" in data_msg:
            if "abort" in data_msg:
                log(f"   ABORT {data_msg}", "bold red")
            elif "_bist" in data_msg:
                ############################################
                await self.discord_client.send_msg(data_msg, "bist_alpy")
            else:
                if "USDT" in data_msg:
                    c = "blue"
                else:
                    c = "magenta"

                log(f" * {_date()} ", end="")
                log(data_msg, c, h=False)
                if "strategy.order.action" not in data_msg:
                    await self.discord_client.send_msg(data_msg, "alpy")

            return

        self.strategy = Strategy(data_msg)
        # if self.strategy.market.lower() == "usdt" and config.btc_wavetrend["30m"] == "red":
        #     log("30m-RED pass", "red")
        #     return

        if not hasattr(self.strategy, "position_alert_msg"):
            raise QuietExit("E: position_alert_msg is empty")

        if "enter" not in self.strategy.position_alert_msg:
            return
        elif self.strategy.market.lower() == "btc" and self.strategy.is_sell():
            log("warning: ignore BTC pair, no need to sell")

        await self._trade()

    async def alert_main(self, data_msg) -> None:
        config.btc_wavetrend["30m"] = data_msg

    # FUTURES #
    async def _order(self, quantity, _type="MARKET"):
        """Open futures orders in given direction."""
        try:
            # await self.bot_async.set_leverage(self.strategy.symbol, 1)  # consumes time
            await create_market_order(self.strategy.symbol, quantity, self.strategy.side)
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e):
                log(f"E: {e} qty={quantity}")
                decimal = self.get_decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening sell order with new qty={_quantity}")
                if float(_quantity) > 0:
                    return await self._order(_quantity)
                else:
                    log("E: Quantity less than zero, nothing to do.")
                    if self.strategy.size >= 0.5 and self.strategy.size < 1:
                        self.strategy.size = 1
            else:
                if self.strategy.size >= 0.5 and self.strategy.size < 1:
                    log("==> re-opening sell order with new qty=1")
                    self.strategy.size = 1
                    return await self._order(self.strategy.size)

                raise e
