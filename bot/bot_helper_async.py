#!/usr/bin/env python3

import os

from broker._utils.tools import _colorize_traceback, get_decimal_count, log
from broker.libs.math import percent_change
from dotenv import load_dotenv

import bot.helper as helper

load_dotenv(override=True)

TP = float(os.getenv("TP"))
TAKE_PROFIT_LONG = 1.000 + TP
TAKE_PROFIT_SHORT = 1.000 - TP
LOCKED_PERCENT_LIMIT_USDT = float(os.getenv("LOCKED_PERCENT_LIMIT_USDT"))
LOCKED_PERCENT_LIMIT_SPOT = float(os.getenv("LOCKED_PERCENT_LIMIT_SPOT"))
PERCENT_CHANGE_TO_ADD_USDT = float(os.getenv("PERCENT_CHANGE_TO_ADD_USDT"))
PERCENT_CHANGE_TO_ADD_SPOT = float(os.getenv("PERCENT_CHANGE_TO_ADD_SPOT"))
SPOT_MULTIPLY_RATIO = float(os.getenv("SPOT_MULTIPLY_RATIO"))
USDT_MULTIPLY_RATIO = float(os.getenv("USDT_MULTIPLY_RATIO"))


class BotHelperAsync:
    def get_precision(self, price_dict):
        list_price = price_dict["info"]["lastPrice"]
        open_price = price_dict["info"]["openPrice"]
        high_price = price_dict["info"]["highPrice"]
        low_price = price_dict["info"]["lowPrice"]
        close = price_dict["close"]
        change = price_dict["change"]
        weighted_avg_price = price_dict["info"]["weightedAvgPrice"]
        price_list = [list_price, open_price, close, high_price, weighted_avg_price, low_price, change]
        _decimal_count = 0
        for p in price_list:
            _decimal_c = get_decimal_count(p)
            if _decimal_c > _decimal_count:
                _decimal_count = _decimal_c
        return _decimal_count

    async def futures_fetch_ticker(self, asset) -> float:
        price = await helper.exchange.future.fetch_ticker(asset)
        return float(price["last"])

    async def spot_fetch_ticker(self, asset) -> float:
        if "USDT" not in asset and "BTC" not in asset:
            asset = asset + "/BTC"

        price = await helper.exchange.spot.fetch_ticker(asset)
        return float(price["last"])

    async def new_limit_order(self, asset, limit_price):
        """New limit order with the added quantity."""
        symbol = f"{asset}/BTC"
        open_orders = await helper.exchange.spot.fetch_open_orders(symbol)
        for order in open_orders:
            try:
                await helper.exchange.spot.cancel_order(order["id"], symbol)
            except Exception as e:
                _colorize_traceback(e)

        try:
            balance = await self.fetch_balance(asset)
            respone = await helper.exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
            log("==> New limit-order is placed:")
            log(respone, color="cyan")
        except Exception as e:
            log("Failed to create order with", helper.exchange.spot.id, type(e).__name__, str(e), color="red")

    async def spot_limit(self, asset, trades, asset_balance, sum_btc):
        symbol = f"{asset}BTC"
        contracts = 0.0
        _sum = 0.0
        quantity = 0.0
        decimal_count = 0
        for idx, trade in enumerate(reversed(trades)):
            # itaretes order for the related asset
            _decimal_count = get_decimal_count(trade["price"])
            if _decimal_count > decimal_count:
                decimal_count = _decimal_count

            if trade["info"]["isBuyer"]:  # and trade["time"] >= timestamp:
                quantity += float(trade["info"]["qty"])
                if quantity > asset_balance:
                    break

                _sum += float(trade["info"]["qty"]) * float(trade["info"]["price"])
                contracts += float(trade["info"]["qty"])

        entry_price = _sum / contracts
        _price = f"{entry_price:.{decimal_count}f}"
        limit_price = f"{float(_price) * TAKE_PROFIT_LONG:.{decimal_count}f}"
        log(f"==> {asset} quantity={asset_balance} | ", end="")
        log(f"entry_price={_price} | ", end="")
        log(f"limit_price={limit_price} ", end="")
        asset_price = await self.spot_fetch_ticker(asset)
        per = (100.0 * asset_balance * asset_price) / sum_btc
        _per = format(per, ".2f")
        log(f"{_per}% ", color="blue", end="")
        asset_percent_change = percent_change(
            initial=entry_price, change=asset_price - entry_price, is_arrow_print=False
        )
        if asset_percent_change <= PERCENT_CHANGE_TO_ADD_SPOT:
            new_order_size = asset_balance * SPOT_MULTIPLY_RATIO
            log(f"new_order_size={new_order_size} | ", color="blue", end="")
            per = (100.0 * (asset_balance + new_order_size) * asset_price) / sum_btc
            _per = format(per, ".2f")
            log(f"==> {_per} of the total asset value")
            if float(_per) <= LOCKED_PERCENT_LIMIT_SPOT:
                order = self.sport_order(new_order_size, symbol, "BUY")
                log(order)
                await self.new_limit_order(asset, limit_price)
            else:
                new_per = (100.0 * asset_balance * asset_price) / sum_btc
                per_to_buy = LOCKED_PERCENT_LIMIT_SPOT - abs(new_per)
                btc_amount_to_buy = per_to_buy * sum_btc / 100.0
                _new_order_size = btc_amount_to_buy / asset_price
                _new_order_size = f"{_new_order_size:.{decimal_count}f}"
                order = self.sport_order(_new_order_size, symbol, "BUY")
                log(order)
                await self.new_limit_order(asset, limit_price)

        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BTC")
        if not open_orders:
            await self.new_limit_order(asset, limit_price)
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL":
                    if float(limit_price) < float(order["price"]):
                        await self.new_limit_order(asset, limit_price)

    async def fetch_balance(self, code) -> float:
        balance = await helper.exchange.spot.fetch_balance()
        return balance[code]["total"]
