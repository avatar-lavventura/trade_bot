#!/usr/bin/env python3

from contextlib import suppress

from broker._utils._log import log
from broker._utils.tools import decimal_count, percent_change, remove_trailing_zeros, round_float

from bot import cfg, helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.config import config


class BotHelperSpotAsync(BotHelperAsync):
    def __init__(self) -> None:
        self.channel = None
        self.channel_alerts = None

    async def check_position_to_pass(self, asset, _sum, is_limit, per) -> bool:
        if _sum > config.isolated_wallet_limit:
            log("PASS_1", "bold")
            return True

        if float(per) > 80:
            log("PASS_2", "bold")
            return True

        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            log("PASS_3", "bold")
            return True

        log()
        return False

    async def is_limit_order_exist(self, asset, limit_price) -> None:
        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/{cfg.TYPE.upper()}")
        if not open_orders:
            await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL" and float(limit_price) < float(order["price"]):
                    await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())

    def get_decimal_count(self, symbol, value) -> int:
        try:
            return helper.exchange.spot_markets[symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def calculate_entry(self, timestamp_list, ordering, trades, is_return=False):
        decimal = 0
        quantity = 0
        _sum = 0
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = trades[inner_index]
                decimal = self.get_decimal_count(trade["symbol"], trade["price"])
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
                if is_return:
                    key = f"{cfg.TYPE.lower()}_timestamp"
                    config.timestamp[key][trade["symbol"].replace(f"/{cfg.TYPE.upper()}", "")] = trade["timestamp"]
                    return (quantity, _sum, decimal)

        return (quantity, _sum, decimal)

    async def is_cut_loss(self, asset, profit, asset_balance):
        """Close trade with accepted loss."""
        if cfg.TYPE.lower() == "usdt" and profit < -15:
            order = await self.strategy.exchange.create_market_sell_order(f"{asset}/{cfg.TYPE.upper()}", asset_balance)
            order = order["info"]
            with suppress(Exception):
                del order["timeInForce"]
                del order["orderListId"]
                del order["price"]
                del order["status"]
                del order["type"]
                del order["origQty"]
                del order["executedQty"]

            log(order)

    async def spot_limit(self, asset, asset_balance, sum_bal, is_limit=True):
        """Spot limit for SPOT."""
        try:
            since = config.get_spot_timestamp(asset)
            if not since:
                since = config.env[cfg.TYPE].status["timestamp"]
        except:
            since = config.env[cfg.TYPE].status["timestamp"]

        if len(str(since)) == 10:
            since = since * 1000

        trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/{cfg.TYPE.upper()}", since=since)
        ordering = {}
        for idx, trade in enumerate(trades):
            try:
                # In case orders occur in the same timestamp
                ordering[trade["timestamp"]].append(idx)
            except:
                ordering[trade["timestamp"]] = [idx]

        # iterate transactions based on their timestamp
        timestamp_list = sorted(ordering, reverse=True)
        if timestamp_list:
            quantity, _sum, decimal = self.calculate_entry(timestamp_list, ordering, trades)
        else:
            trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/{cfg.TYPE.upper()}")
            ordering = {}
            for idx, trade in enumerate(trades):
                try:
                    ordering[trade["timestamp"]].append(idx)
                except Exception:
                    ordering[trade["timestamp"]] = [idx]

            timestamp_list = sorted(ordering, reverse=True)
            quantity, _sum, decimal = self.calculate_entry(timestamp_list, ordering, trades, is_return=True)

        if quantity == 0:
            if asset in config.SPOT_IGNORE_LIST:
                return 0

            raise Exception(f"quantity is zero asset={asset}")

        entry_price = _sum / quantity
        entry_price = float(f"{entry_price:.{decimal}f}")
        limit_price = f"{entry_price * TP.get_profit_amount(_sum):.{decimal}f}"
        _quantity = format(asset_balance, ".4f")
        log(f"[green]==>[/green] {asset} q={remove_trailing_zeros(_quantity)} | e={entry_price} | ", "bold", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"l={limit_price} | ", "bold", end="")

        if entry_price == limit_price:
            raise Exception(f"entry_price and limit_price are same, equal to {entry_price}")

        asset_price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")
        log(f"p={asset_price} ", "bold", end="")
        per = format((100.0 * asset_balance * asset_price) / sum_bal, ".2f")
        profit = (asset_price - entry_price) * quantity
        if profit != 0:
            if cfg.TYPE.lower() == "usdt":
                log(format(profit, ".2f"), "bold green" if profit > 0 else "bold red", end="")
            else:
                log(format(profit * 1000, ".5f"), "bold green" if profit > 0 else "bold red", end="")

            per_change = percent_change(
                initial=entry_price, change=asset_price - entry_price, end="", is_arrow_print=False
            )
        else:
            per_change = 0

        if cfg.TYPE.lower() == "usdt":
            log(f"| [bold magenta]{format(_sum, '.2f')} ([yellow]{per}%[/yellow]) ", end="")
        else:
            log(f"| [bold magenta]{format(_sum * 1000, '.4f')} ([yellow]{per}%[/yellow]) ", end="")

        cfg.locked_balance += float(per)
        msg = f"**{asset}** e={entry_price} `{format(profit, '.1f')}` ({format(per_change, '.2f')}%) `{round(_sum)}$`\n"
        if self.channel:
            cfg.discord_message_full += msg
            if _sum > config.discord_msg_above_usdt and profit < 0:
                cfg.discord_message += msg

        # self.is_cut_loss(asset, profit, asset_balance)
        if asset in config.SPOT_IGNORE_LIST:
            log()
            return profit
        elif (cfg.TYPE.lower() == "usdt" and config.env["usdt"].status["free"] < 15) or (
            cfg.TYPE.lower() == "btc" and float(config.env["btc"].status["free"]) < 0.0003
        ):
            log()
        elif not await self.check_position_to_pass(asset, _sum, is_limit, per):
            if per_change <= -2 and per_change <= config.env[cfg.TYPE].percent_change_to_add:
                new_order_size = asset_balance * config.env[cfg.TYPE].multiply_ratio
                if new_order_size * asset_price < 10:
                    # usdt_multiply_ratio may 0.1, minimum order should be more than 10$
                    new_order_size = asset_balance * 1.05

                log(f"new_order_size={new_order_size}", "bold")
                per = (100.0 * (asset_balance + new_order_size) * asset_price) / sum_bal
                log(f"==> {format(float(per), '.2f')}% => {format(float(per), '.2f')}% of the total asset value")
                order = await self.spot_order(new_order_size, f"{asset}/{cfg.TYPE.upper()}", "BUY")
                if order:
                    log(order["info"])
                    await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())

        await self.is_limit_order_exist(asset, limit_price)
        return profit
