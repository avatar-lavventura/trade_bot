#!/usr/bin/env python3


from contextlib import suppress

from broker._utils._log import log
from broker._utils.tools import decimal_count, percent_change, round_float

from bot import cfg
from bot import config as helper
from bot.config import config
from bot.take_profit import TakeProfit

TP = TakeProfit()


class BotHelperAsync:
    async def spot_limit(self, asset, asset_balance, sum_bal, is_limit=True):
        """
        * Python sort list based on key sorted list:
         __ https://stackoverflow.com/a/18016874/2402577
        """
        decimal = 0
        _sum = 0
        quantity = 0
        try:
            since = config.get_spot_timestamp(asset)
            if not since:
                since = config.env[cfg.TYPE].status["timestamp"]
        except:
            since = config.env[cfg.TYPE].status["timestamp"]

        trades = await helper.exchange.spot.fetch_my_trades(asset + "/BTC", since=since)
        ordering = {}
        for idx, trade in enumerate(trades):
            if trade["timestamp"] in ordering:
                # in case orders occur in the same timestamp
                ordering[trade["timestamp"]].append(idx)
            else:
                ordering[trade["timestamp"]] = [idx]

        #: sort transactions based on their timestamp
        timestamp_list = sorted(ordering, reverse=True)
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = trades[inner_index]
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
        limit_price = f"{entry_price * TP.get_profit_amount():.{decimal}f}"
        log(f"==> {asset} quantity={asset_balance} | entry_price={entry_price} | ", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"limit_price={limit_price} ", end="")

        try:
            asset_price = await self.spot_fetch_ticker(asset)
        except Exception as e:
            raise Exception(f"asset({asset}) is not found in ticker") from e

        per = format((100.0 * asset_balance * asset_price) / sum_bal, ".2f")
        log(f"{per}% ", "blue", end="")
        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            return

        asset_percent_change = percent_change(initial=entry_price, change=asset_price - entry_price, is_arrow=False)
        if asset_percent_change <= config.SPOT_PERCENT_CHANGE_TO_ADD and float(per) < 50:
            new_order_size = asset_balance * config.SPOT_MULTIPLY_RATIO
            log(f"==> new_order_size={new_order_size} | {per} of the total asset value", end="")
            if float(per) <= config.SPOT_locked_percent_limit:
                order = await self.spot_order(new_order_size, f"{asset}/BTC", "BUY")
                order = order["info"]
                with suppress(Exception):
                    del order["type"]
                    del order["timeInForce"]
                    del order["status"]
                    del order["executedQty"]
                    del order["cummulativeQuoteQty"]
                    del order["orderListId"]
                    del order["fills"]
                    del order["orderId"]
                    del order["clientOrderId"]
                    del order["transactTime"]

                log(f"order={order}", "bold")
                await self.new_limit_order(asset, limit_price)
            else:
                new_per = (100.0 * asset_balance * asset_price) / sum_bal
                per_to_buy = config.SPOT_locked_percent_limit - abs(new_per)
                btc_amount_to_buy = per_to_buy * sum_bal / 100.0
                _new_order_size = btc_amount_to_buy / asset_price
                _new_order_size = f"{_new_order_size:.{decimal}f}"
                order = await self.spot_order(_new_order_size, f"{asset}/BTC", "BUY")
                log(order["info"], "bold")
                await self.new_limit_order(asset, limit_price)

        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BTC")
        if open_orders:
            for order in open_orders:
                if order["info"]["side"] == "SELL" and float(limit_price) < float(order["price"]):
                    await self.new_limit_order(asset, limit_price)
        else:
            await self.new_limit_order(asset, limit_price)

        return 0
