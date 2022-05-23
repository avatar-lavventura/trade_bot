#!/usr/bin/env python3

from broker._utils._async import _sleep
from broker._utils._log import br, log
from broker._utils.tools import print_tb
from broker.errors import QuietExit

from bot import helper
from bot.config import config
from bot.trade_async import BotHelper


class BotHelperUsdtperp(BotHelper):
    def __init__(self) -> None:
        pass

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

    def get_future_position(self, positions):
        for pos in positions:
            if abs(float(pos["info"]["isolatedWallet"])) > 0:
                return (
                    float(pos["entryPrice"]),
                    float(pos["info"]["positionAmt"]),
                    abs(float(pos["info"]["isolatedWallet"])),
                )

        raise Exception("order related to the symbol couldn't be found")

    def get_exchange_future_timestamp(self) -> None:
        self.unix_timestamp_ms = helper.exchange.get_future_timestamp()
        self.current_bar_index_local = int(int((self.unix_timestamp_ms - 1) / 900))

    async def calculate_futures_size(self) -> None:
        self.strategy.size = 0
        _initial_usdt_qty = 15
        _initial_usdt_qty_short = 15
        output = await self.symbol_price(self.strategy.symbol, "future")
        last_price = output["last"]
        if last_price == 0:
            raise Exception("last_price is zero")

        if self.strategy.is_buy():
            if self.strategy.time_duration == "1m":
                initial_amount = config.initial_usdt_qty_long["1m"] / last_price
            else:
                initial_amount = _initial_usdt_qty / last_price
        else:  # short
            if self.strategy.time_duration == "1m":
                initial_amount = config.initial_usdt_qty_short["1m"] / last_price
            else:
                initial_amount = _initial_usdt_qty_short / last_price

        self.strategy.size = float(self.get_initial_amount(initial_amount, "USDT"))
        self.futues_size_check(last_price)

    def pre_check_usdtperp(self, free_balance, raise_msg) -> None:
        # futures_locked_percent = config.status["futures"]["locked_per"]
        # if self.strategy.time_duration != "1m":
        #     if futures_locked_percent > config.cfg["root"]["usdtperp"]["stop_locked_per"]:
        #         raise QuietExit(f"locked_percent={int(futures_locked_percent)}% PASS")
        _initial_usdt_qty_short = 15
        duration = self.strategy.time_duration
        if self.strategy.side == "BUY":
            if duration == "1m" and free_balance < config.initial_usdt_qty_long[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_balance < config._initial_usdt_qty:
                raise QuietExit(raise_msg)
        elif self.strategy.side == "SELL":
            if free_balance < config.initial_usdt_qty_short[duration]:
                raise QuietExit(raise_msg)

            if duration in config.base_durations and free_balance < _initial_usdt_qty_short:
                raise QuietExit(raise_msg)

    async def sell(self):
        if self.strategy.market == "USDTPERP":
            try:
                await self.both_side_order()
                await self.futures_limit_order()
            except Exception as e:
                print_tb(e)  # order related to the symbol couldn't be found at 3:00 AM"

    async def get_futures_open_position_count(self, is_print=False) -> int:
        """Return number of open positions.

        initial_margin is considered as `isolatedWallet`.
        """
        try:
            positions = await helper.exchange.future.fetch_positions()
        except Exception as e:
            print_tb(e)
            raise e

        count = 0
        for position in positions:
            if abs(float(position["info"]["isolatedWallet"])) > 0:
                count += 1
                if is_print:
                    log(position, "bold blue")

        return count

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
            log("#> opening limit order: ", end="")
            log(f"entry_price={entry_price} ", "bold", end="")
            decimal = self.get_decimal_count(entry_price)
            await self._limit(amount, entry_price, isolated_wallet, decimal)
        except Exception as e:
            print_tb(str(e))
