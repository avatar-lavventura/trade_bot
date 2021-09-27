#!/usr/bin/env python3

from contextlib import suppress

from filelock import FileLock

from bot import helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.config import config
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import _colorize_traceback, decimal_count, percent_change, round_float


class BotHelperUsdtAsync(BotHelperAsync):
    def __init__(self):
        pass

    ############
    # SPOT USDT#
    ############
    # async def spot_balance(self, is_limit=True):
    #     """Calculate USDT balance in spot."""
    #     usdt_amount = 0.0
    #     sum_btc = 0.0
    #     count = 0
    #     balances = await helper.exchange.spot.fetch_balance()
    #     for balance in balances["info"]["balances"]:
    #         asset = balance["asset"]
    #         if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
    #             quantity = float(balance["free"]) + float(balance["locked"])
    #             if asset == "BTC":
    #                 sum_btc += quantity
    #             else:
    #                 if asset not in ["USDT", "BNB"]:
    #                     # TODO: check float(balance["free"]) USDT value if > 1.0 USDT
    #                     count += 1
    #                     price = await self.spot_fetch_ticker(asset)
    #                     sum_btc += quantity * float(price)
    #                 elif asset == "USDT":
    #                     usdt_amount = quantity

    #     current_btc_price_USD = await self.spot_fetch_ticker("BTC/USDT")
    #     own_usd = sum_btc * float(current_btc_price_USD)
    #     if sum_btc > 0.0:
    #         log(" * Spot=%.8f BTC == %.2f USDT" % (sum_btc, own_usd))

    #     for balance in balances["info"]["balances"]:
    #         asset = balance["asset"]
    #         if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
    #             with suppress(Exception):
    #                 btc_quantity = float(balance["free"]) + float(balance["locked"])
    #                 if asset not in ["BTC", "BNB", "USDT"]:
    #                     await self.spot_limit(asset, btc_quantity, sum_btc, is_limit)

    #     with FileLock(config.status.fp_lock, timeout=1):
    #         config.status["spot"]["pos_count"] = count

    #     return own_usd, float(usdt_amount)

    # async def spot_order(self, quantity, symbol, side):
    #     try:
    #         log(f"==> order_quantity={quantity}")
    #         return await helper.exchange.spot.create_market_buy_order(symbol, quantity)
    #     except Exception as e:
    #         if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
    #             log(f"E: {e} quantity={quantity}")
    #             decimal = decimal_count(quantity)
    #             _quantity = f"{float(quantity):.{decimal - 1}f}"
    #             log(f"==> re-opening {side} order, quantity={_quantity}")
    #             if float(_quantity) > 0.0:
    #                 return await self.spot_order(_quantity, symbol, side)
    #             else:
    #                 log("E: quantity is zero, nothing to do.")
    #         elif "Filter failure: MIN_NOTIONAL" == getattr(e, "message", repr(e)) and quantity >= 1:
    #             quantity += 0.1
    #             quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
    #             log(f"==> re-opening {side} order, quantity={quantity}")
    #             return await self.spot_order(quantity, symbol, side)
    #         else:
    #             _colorize_traceback(e)
    #             raise e

    # async def spot_fetch_ticker(self, asset) -> float:
    #     if "USDT" not in asset and "BTC" not in asset:
    #         asset = asset + "/BTC"

    #     price = await helper.exchange.spot.fetch_ticker(asset)
    #     return float(price["last"])

    # async def new_limit_order(self, asset, limit_price):
    #     """Create new limit order with the added quantity."""
    #     symbol = f"{asset}/BTC"
    #     open_orders = await helper.exchange.spot.fetch_open_orders(symbol)
    #     for order in open_orders:
    #         try:
    #             await helper.exchange.spot.cancel_order(order["id"], symbol)
    #         except Exception as e:
    #             _colorize_traceback(e)

    #     try:
    #         balance = await self.fetch_balance(asset)
    #         respone = await helper.exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
    #         log("==> New limit-order is placed:")
    #         log(respone, "cyan")
    #     except Exception as e:
    #         log("Failed to create order with", helper.exchange.spot.id, type(e).__name__, str(e), "red")

    # async def fetch_balance(self, code) -> float:
    #     balance = await helper.exchange.spot.fetch_balance()
    #     return balance[code]["total"]

    async def spot_limit_usdt(self, asset, asset_balance, sum_btc, is_limit=True):
        """Spot limit for USDT."""
        symbol = f"{asset}/USDT"
        _sum = 0.0
        quantity = 0.0
        decimal = 0
        try:
            _since = config.get_spot_timestamp(asset)
            if not _since:
                _since = config.SPOT_TIMESTAMP
        except:
            _since = config.SPOT_TIMESTAMP

        if len(str(_since)) == 10:
            _since = _since * 1000

        trades = await helper.exchange.spot.fetch_my_trades(asset + "/USDT", since=_since)
        # all_trades = trades + trades_usdt  # merge USDT transactions
        all_trades = trades
        ordering = {}
        for idx, trade in enumerate(all_trades):
            try:
                # In case orders occur in the same timestamp
                ordering[trade["timestamp"]].append(idx)
            except:
                ordering[trade["timestamp"]] = [idx]

        # Iterate transactions based on their timestamp
        timestamp_list = sorted(ordering, reverse=True)
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = all_trades[inner_index]
                decimal = decimal_count(trade["price"])
                qty = float(trade["info"]["qty"])
                trade_cost = trade["cost"]  # ignoring fees
                if trade["info"]["isBuyer"]:
                    quantity += qty
                    _sum += trade_cost
                else:
                    quantity -= qty
                    _sum -= trade_cost

                quantity = round_float(quantity, 8)
                _sum = round_float(_sum, 8)

        entry_price = _sum / quantity
        entry_price = float(f"{entry_price:.{decimal}f}")
        limit_price = f"{entry_price * TP.get_profit_amount('long'):.{decimal}f}"
        log(f"==> {asset} quantity={asset_balance} | ", end="")
        log(f"entry_price={entry_price} | ", "bold", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"limit_price={limit_price} ", end="")

        asset_price = await self.spot_fetch_ticker(asset)
        per = (100.0 * asset_balance * asset_price) / sum_btc
        _per = format(per, ".2f")
        log(f"{_per}% ", "blue", end="")
        asset_percent_change = percent_change(
            initial=entry_price, change=asset_price - entry_price, is_arrow_print=False
        )
        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            return

        # if asset_percent_change <= config.SPOT_PERCENT_CHANGE_TO_ADD and _per < 50.0:
        #     new_order_size = asset_balance * config.SPOT_MULTIPLY_RATIO
        #     log(f"new_order_size={new_order_size} | ", "blue", end="")
        #     per = (100.0 * (asset_balance + new_order_size) * asset_price) / sum_btc
        #     _per = format(per, ".2f")
        #     log(f"==> {_per} of the total asset value")
        #     if float(_per) <= config.SPOT_LOCKED_PERCENT_LIMIT:
        #         order = await self.spot_order(new_order_size, _symbol, "BUY")
        #         log(order["info"])
        #         await self.new_limit_order(asset, limit_price)
        #     else:
        #         new_per = (100.0 * asset_balance * asset_price) / sum_btc
        #         per_to_buy = config.SPOT_LOCKED_PERCENT_LIMIT - abs(new_per)
        #         btc_amount_to_buy = per_to_buy * sum_btc / 100.0
        #         _new_order_size = btc_amount_to_buy / asset_price
        #         _new_order_size = f"{_new_order_size:.{decimal}f}"
        #         order = await self.spot_order(_new_order_size, _symbol, "BUY")
        #         log(order["info"])
        #         await self.new_limit_order(asset, limit_price)

        # open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BTC")
        # if not open_orders:
        #     await self.new_limit_order(asset, limit_price)
        # else:
        #     for order in open_orders:
        #         if order["info"]["side"] == "SELL":
        #             if float(limit_price) < float(order["price"]):
        #                 await self.new_limit_order(asset, limit_price)
