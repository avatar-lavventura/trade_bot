#!/usr/bin/env python3

from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import decimal_count, percent_change, round_float

from bot import helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.config import config


class BotHelperUsdtAsync(BotHelperAsync):
    def __init__(self):
        pass

    async def spot_limit_usdt(self, asset, asset_balance, sum_usdt, is_limit=True):
        """Spot limit for USDT."""
        quantity = 0.0
        decimal = 0
        _sum = 0.0
        try:
            since = config.get_spot_timestamp(asset)
            if not since:
                since = config.SPOT_TIMESTAMP
        except:
            since = config.SPOT_TIMESTAMP

        if len(str(since)) == 10:
            since = since * 1000

        trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/USDT", since=since)
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
            log(f"limit_price={limit_price} ", "bold", end="")

        asset_usdt_price = await self.spot_fetch_ticker(f"{asset}USDT")
        per = (100.0 * asset_balance * asset_usdt_price) / sum_usdt
        _per = format(per, ".2f")
        log(f"{_per}% ", "blue", end="")
        profit = (asset_usdt_price - entry_price) * quantity
        if profit > 0:
            log(format(profit, ".2f"), "bold green", end="")
        else:
            log(format(profit, ".2f"), "bold red", end="")

        asset_percent_change = percent_change(
            initial=entry_price, change=asset_usdt_price - entry_price, is_arrow_print=False
        )
        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            return

        if asset_percent_change <= config.usdt_percent_change_to_add:  #  and float(_per) < 50.0
            new_order_size = asset_balance * config.usdt_multiply_ratio
            log(f"new_order_size={new_order_size} | ", "bold blue", end="")
            per = (100.0 * (asset_balance + new_order_size) * asset_usdt_price) / sum_usdt
            log(f"==> {_per} of the total asset value")
            # if float(_per) > config.SPOT_LOCKED_PERCENT_LIMIT:
            #     # TODO: Calculate percent on full money on futures as well
            #     new_per = (100.0 * asset_balance * asset_usdt_price) / sum_usdt
            #     per_to_buy = config.SPOT_LOCKED_PERCENT_LIMIT - abs(new_per)
            #     usdt_amount_to_buy = per_to_buy * sum_usdt / 100.0
            #     _new_order_size = usdt_amount_to_buy / asset_usdt_price
            #     new_order_size = f"{_new_order_size:.{decimal}f}"

            order = await self.spot_order(new_order_size, f"{asset}/USDT", "BUY")
            log(order["info"])
            await self.new_limit_order(asset, limit_price, "USDT")

        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/USDT")
        if not open_orders:
            await self.new_limit_order(asset, limit_price, "USDT")
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL" and float(limit_price) < float(order["price"]):
                    await self.new_limit_order(asset, limit_price, "USDT")
