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
        if asset == "LUNA":
            open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BUSD")
        else:
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

    def calculate_entry(self, timestamp_list, ordering, trades, is_return=False) -> (float, float, int):
        _sum = 0
        decimal = 0
        quantity = 0.0
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = trades[inner_index]
                if float(trade["info"]["commission"]) > 0:
                    decimal = self.get_decimal_count(trade["symbol"], trade["price"])
                    qty = float(trade["info"]["qty"])
                    if trade["info"]["isBuyer"]:
                        quantity += qty
                        _sum += trade["cost"]
                    elif (
                        not cfg.IGNORE_SOLD_QUANTITY
                        or "ignore_sold" in trade
                        or trade["symbol"] in cfg._IGNORE_SOLD_QUANTITY
                    ):
                        quantity -= qty
                        _sum -= trade["cost"]

                    quantity = round_float(quantity, 8)
                    _sum = round_float(_sum, 8)
                    if is_return:
                        key = f"{cfg.TYPE.lower()}_timestamp"
                        config.timestamp[key][trade["symbol"].replace(f"/{cfg.TYPE.upper()}", "")] = trade["timestamp"]
                        return (quantity, _sum, decimal)

        return (quantity, _sum, decimal)

    async def is_cut_loss(self, asset, profit, qty) -> None:
        """Close trade with accepted loss."""
        if cfg.TYPE.lower() == "usdt" and profit < -15:
            order = await self.strategy.exchange.create_market_sell_order(f"{asset}/{cfg.TYPE.upper()}", qty)
            order = order["info"]
            with suppress(Exception):
                del order["timeInForce"]
                del order["orderListId"]
                del order["price"]
                del order["status"]
                del order["type"]
                del order["origQty"]
                del order["executedQty"]

            log(f"## CUT LOSS for {asset}={profit}", "bold blue")
            log(order)

    async def add_to_position(self, asset, qty, asset_price, sum_bal, limit_price) -> None:
        new_order_size = qty * config.env[cfg.TYPE].multiply_ratio
        if new_order_size * asset_price < 10:
            # usdt_multiply_ratio may 0.1, minimum order should be more than 10$
            new_order_size = qty * 1.05

        log(f"new_order_size={new_order_size}", "bold")
        per = (100.0 * (qty + new_order_size) * asset_price) / sum_bal
        log(f"==> {format(float(per), '.2f')}% => {format(float(per), '.2f')}% of the total asset value")
        order = await self.spot_order(new_order_size, f"{asset}/{cfg.TYPE.upper()}", "BUY")
        if order:
            log(order["info"])
            await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())

    async def spot_limit(self, asset, asset_qty, sum_bal, is_limit=True) -> float:
        """Limit order for the SPOT market.

        :param asset_qty: complete quantity of the asset, could be left over due the 0 BNB

        __ https://stackoverflow.com/questions/70318352/how-to-get-the-price-of-a-crypto-at-a-given-time-in-the-past
        """
        if asset == "LUNA":
            try:
                since = config.get_spot_timestamp_busd(asset)
                if not since:
                    since = config.env["busd"].status["timestamp"]
            except:
                since = config.env["busd"].status["timestamp"]
        else:
            try:
                since = config.get_spot_timestamp(asset)
                if not since:
                    since = config.env[cfg.TYPE].status["timestamp"]
            except:
                since = config.env[cfg.TYPE].status["timestamp"]

        if len(str(since)) == 10:
            since = since * 1000

        if asset == "LUNA":
            trades = await helper.exchange.spot.fetch_my_trades("LUNA/BUSD", since=since)
        else:
            trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/{cfg.TYPE.upper()}", since=since)

        if cfg.TYPE.lower() == "btc" and asset != "LUNA":
            _trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/USDT", since=since)
            with suppress(Exception):
                for idx, trade in enumerate(_trades):
                    if not trade["info"]["isBuyer"]:
                        ts = int(trade["info"]["time"])
                        response = await helper.exchange.spot.fetch_ohlcv("BTC/USDT", "1m", ts, 1)
                        trade["cost"] = trade["cost"] / float(response[0][1])
                        trade["ignore_sold"] = True
                        trades.append(trade)
        # else:
        #     _trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/BTC", since=since)
        #     with suppress(Exception):
        #         for idx, trade in enumerate(_trades):
        #             if not trade["info"]["isBuyer"]:
        #                 ts = int(trade["info"]["time"])
        #                 response = await helper.exchange.spot.fetch_ohlcv("BTC/USDT", "1m", ts, 1)
        #                 breakpoint()  # DEBUG
        #                 trade["cost"] = trade["cost"] * float(response[0][1])
        #                 trade["ignore_sold"] = True
        #                 trades.append(trade)
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
            qty, _sum, decimal = self.calculate_entry(timestamp_list, ordering, trades)
        else:
            trades = await helper.exchange.spot.fetch_my_trades(f"{asset}/{cfg.TYPE.upper()}")
            ordering = {}
            for idx, trade in enumerate(trades):
                try:
                    ordering[trade["timestamp"]].append(idx)
                except Exception:
                    ordering[trade["timestamp"]] = [idx]

            timestamp_list = sorted(ordering, reverse=True)
            qty, _sum, decimal = self.calculate_entry(timestamp_list, ordering, trades, is_return=True)

        if asset_qty == 0:
            log(f"E: float division by zero asset={asset}")
            return 0

        if asset_qty != qty:
            log(f"warning: wrong calculation for {asset}. {asset_qty} -- {qty}")

        entry_price = _sum / qty
        entry_price = float(f"{entry_price:.{decimal}f}")
        if asset == "LUNA":
            entry_price = 0.00024

        limit_price = f"{entry_price * TP.get_profit_amount(_sum):.{decimal}f}"
        qty_str = format(qty, ".4f")
        log(f"[green]**[/green] {asset} q={remove_trailing_zeros(qty_str)} | e={entry_price} | ", "bold", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"l={limit_price} | ", "bold", end="")

        if entry_price == limit_price:
            raise Exception(f"entry_price and limit_price are same, equal to {entry_price}")

        if asset == "LUNA":
            asset_price = await self.spot_fetch_ticker(f"{asset}BUSD")
        else:
            asset_price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")

        log(f"p={asset_price} ", "bold", end="")
        per = format((100.0 * qty * asset_price) / sum_bal, ".2f")
        profit = (asset_price - entry_price) * qty
        if profit == 0:
            per_change = 0
        else:
            if cfg.TYPE.lower() == "usdt":
                log(format(profit, ".2f"), "bold green" if profit > 0 else "bold red", end="")
            else:
                log(format(profit * 1000, ".5f"), "bold green" if profit > 0 else "bold red", end="")

            per_change = percent_change(
                initial=entry_price, change=asset_price - entry_price, end="", is_arrow_print=False
            )

        if cfg.TYPE.lower() == "usdt":
            log(f"| [bold magenta]{format(_sum, '.2f')} ([yellow]{per}%[/yellow]) ", end="")
        else:
            log(f"| [bold magenta]{format(_sum * 1000, '.4f')} ([yellow]{per}%[/yellow]) ", end="")

        cfg.locked_balance += float(per)
        msg = f"**{asset}** {entry_price} p={asset_price} "
        if cfg.TYPE.lower() == "usdt":
            msg = f"{msg}`{format(profit, '.1f')}` ({format(per_change, '.2f')}%) `{round(_sum)}$`\n"
        else:
            msg = f"{msg}`{format(profit * 1000, '.5')}` ({format(per_change, '.2f')}%) | {per}% \n"

        if self.channel:
            if cfg.discord_message_full == ".\n" and cfg.TYPE.lower() == "usdt":
                special_char = ""
                if config.btc_wavetrend["30m"] == "green":
                    special_char = "+"
                else:
                    special_char = "-"

                cfg.discord_message_full = (
                    f"```diff\n{special_char} BTCUSDT={int(cfg.BTCUSDT_PRICE)} wt=[{config.btc_wavetrend['30m']}]\n```"
                )

            cfg.discord_message_full += msg
            if cfg.TYPE.lower() == "usdt" and _sum > config.discord_msg_above_usdt and profit < 0:
                cfg.discord_message += msg
            elif cfg.TYPE.lower() == "btc" and profit < 0:  # TODO: improve
                cfg.discord_message += msg

        # self.is_cut_loss(asset, profit, qty)
        config.reload_wavetrend()
        if asset in config.SPOT_IGNORE_LIST:
            log()
            return profit
        elif (cfg.TYPE.lower() == "usdt" and config.env["usdt"].status["free"] < 15) or (
            cfg.TYPE.lower() == "btc" and float(config.env["btc"].status["free"]) < 0.0003
        ):
            log()
        elif (
            not await self.check_position_to_pass(asset, _sum, is_limit, per)
            and per_change <= -2
            and per_change <= config.env[cfg.TYPE].percent_change_to_add
            and config.btc_wavetrend["30m"] == "green"  # wait till wt for btc is green in 30m
        ):
            await self.add_to_position(asset, qty, asset_price, sum_bal, limit_price)

        # if config.btc_wavetrend["30m"] == "red":
        #     log("PASS: btc_wavetrend is red nothing to do", "red")

        await self.is_limit_order_exist(asset, limit_price)
        return profit
