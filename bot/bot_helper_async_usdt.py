#!/usr/bin/env python3

from contextlib import suppress
from typing import Tuple

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
            log("pass_a", "bold")
            return True

        if float(per) > 80:
            log("pass_b", "bold")
            return True

        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            log("pass_c", "bold")
            return True

        log()
        return False

    async def is_limit_order_exist(self, asset, limit_price) -> None:
        market = cfg.TYPE.upper()
        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/{market}")
        if open_orders:
            for order in open_orders:
                if order["info"]["side"] == "SELL":
                    if float(limit_price) < float(order["price"]) or cfg.BALANCES[asset]["total"] > float(
                        order["amount"]
                    ):
                        q_per_change = abs(
                            percent_change(
                                cfg.BALANCES[asset]["total"],
                                cfg.BALANCES[asset]["total"] - order["amount"],
                                is_print=False,
                            )
                        )
                        if q_per_change > 0.01:  # prevent 0.01% wrong quantity calculations
                            await self.new_limit_order(asset, limit_price, market)
        else:
            await self.new_limit_order(asset, limit_price, market)

    def get_decimal_count(self, symbol, value) -> int:
        try:
            return helper.exchange.spot_markets[symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def calculate_entry(self, timestamp_list, ordering, trades, asset, asset_qty) -> Tuple[float, float, int]:
        _sum = 0.0
        quantity = 0.0
        quantity_consider_sold = 0.0
        first_sell_flag = False
        latest_buy_trade_idx = 0
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = trades[inner_index]
                # log(trade)
                # log(trade["info"])  # debug purposes
                if float(trade["info"]["commission"]) > 0:
                    qty = float(trade["info"]["qty"])
                    if trade["info"]["isBuyer"]:
                        quantity += qty
                        quantity_consider_sold += qty
                        _sum += trade["cost"]
                        latest_buy_trade_idx = inner_index
                        latest_ts = trade["timestamp"]
                    else:
                        quantity_consider_sold -= qty
                        if not first_sell_flag and quantity == asset_qty:
                            # latest trade is buyer and equat to current asset number
                            _trade = trades[latest_buy_trade_idx]
                            latest_ts = _trade["timestamp"]
                            if latest_ts != 0:
                                # TODO: in 10 seconds if ts not updated entry calculated wrong
                                # and the gain may added && maliyet azalmis oluyor
                                #: sets timestamp for the asset
                                config.timestamp[f"{cfg.TYPE}_timestamp"][asset] = latest_ts

                            return (quantity, _sum)

                        first_sell_flag = True
                        if (
                            not cfg.IGNORE_SOLD_QUANTITY
                            or "ignore_sold" in trade
                            or trade["symbol"] in cfg._IGNORE_SOLD_QUANTITY
                        ):
                            quantity -= qty
                            _sum -= trade["cost"]

                    # if quantity_consider_sold == 0:
                    #     quantity = 0
                    #     _sum = 0  # reset previous trades
                    #     # latest_ts = trade["timestamp"] + 1
                    #     breakpoint()  # DEBUG

                    quantity = round_float(quantity, 8)
                    _sum = round_float(_sum, 8)

        # breakpoint()  # DEBUG
        return (quantity, _sum)

    async def is_cut_loss(self, asset, profit, qty) -> None:
        """Close trade with accepted loss."""
        if cfg.TYPE == "usdt" and profit < -15:
            order = await self.strategy.exchange.create_market_sell_order(f"{asset}/{cfg.TYPE.upper()}", qty)
            order = order["info"]
            with suppress(Exception):
                for name in ["timeInForce", "orderListId", "price", "status", "type", "origQty", "executedQty"]:
                    del order[name]

            log(f"## CUT LOSS for {asset}={profit}", "bold blue")
            log(order)

    async def add_to_position(self, asset, qty, asset_price, sum_bal, limit_price) -> None:
        new_qty = qty * config.env[cfg.TYPE].multiply_ratio
        if new_qty * asset_price < 10:
            # usdt_multiply_ratio may 0.1, minimum order should be more than 10$
            new_qty = qty * 1.05

        per = (100.0 * new_qty * asset_price) / sum_bal
        log(f"==> new_order_qty={new_qty} | {format(float(per), '.2f')}% of the total asset")
        order = await self.spot_order(new_qty, f"{asset}/{cfg.TYPE.upper()}", "BUY")
        if order:
            log(order["info"])
            await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())

    def ll(self, value):
        if cfg.TYPE in ["usdt", "busd"]:
            return value
        else:
            return format(float(value) * 1000, ".5f")

    async def spot_limit(self, asset, asset_qty, sum_bal, is_limit=True) -> float:
        """Limit order for the SPOT market.

        :param asset_qty: complete quantity of the asset, could be left over due the 0 BNB

        __ https://stackoverflow.com/questions/70318352/how-to-get-the-price-of-a-crypto-at-a-given-time-in-the-past
        """
        # TODO: could be done in thread
        _type = cfg.TYPE
        symbol: str = f"{asset}/{_type.upper()}"
        since = await config.get_spot_timestamp(asset)
        if len(str(since)) == 10:
            since = since * 1000

        decimal: int = helper.exchange.spot_markets[symbol]["precision"]["price"]
        if asset in config.cfg["root"][cfg.TYPE]["entry_prices"]:
            entry_price = config.cfg["root"][cfg.TYPE]["entry_prices"][asset]
            qty_to_consider = asset_qty
            _sum = float(entry_price) * asset_qty
        else:
            trades = await helper.exchange.spot.fetch_my_trades(symbol, since=since)
            if _type == "btc":
                with suppress(Exception):
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

            #: iterate transactions based on their timestamp
            timestamp_list = sorted(ordering, reverse=True)
            if timestamp_list:
                qty, _sum = self.calculate_entry(timestamp_list, ordering, trades, asset, asset_qty)
            else:
                trades = await helper.exchange.spot.fetch_my_trades(symbol)
                ordering = {}
                for idx, trade in enumerate(trades):
                    try:
                        ordering[trade["timestamp"]].append(idx)
                    except Exception:
                        ordering[trade["timestamp"]] = [idx]

                timestamp_list = sorted(ordering, reverse=True)
                qty, _sum = self.calculate_entry(timestamp_list, ordering, trades, asset, asset_qty)

            if asset_qty == 0:
                log(f"E: float division by zero asset={asset}")
                return 0

            if qty == 0:
                return 0

            if (
                abs(float(asset_qty) - float(qty)) > 0.000000000001
                and asset not in config.cfg["root"][cfg.TYPE]["entry_prices"]
            ):
                log(f"warning: wrong calculation for {symbol} {asset_qty} == {qty}", is_write=False)

            qty_to_consider = qty
            if asset_qty > qty:
                #: could be additional gain from the margin trading.
                qty_to_consider = asset_qty

            entry_price = _sum / qty_to_consider
            entry_price = float(f"{entry_price:.{decimal}f}")

        with suppress(Exception):
            if asset in config.cfg["root"][cfg.TYPE]["entry_prices"]:
                #: sets entry price with the value read from the config.yaml file
                entry_price = config.cfg["root"][cfg.TYPE]["entry_prices"][asset]

        limit_price = f"{entry_price * TP.get_profit_amount(_sum):.{decimal}f}"
        if _type in ["usdt", "busd"]:
            qty_str = remove_trailing_zeros(format(qty_to_consider, ".2f"))
        else:
            qty_str = remove_trailing_zeros(format(qty_to_consider, ".4f"))

        log(f"[green]**[/green] {asset} q={qty_str} e={self.ll(entry_price)} ", "bold", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"l={self.ll(limit_price)} ", "bold", end="")

        if entry_price == limit_price:
            raise Exception(f"entry_price and limit_price are same and equal to {entry_price}")

        asset_price = await self.spot_fetch_ticker(f"{asset}{_type.upper()}")
        log(f"p={self.ll(asset_price)} ", "bold", end="")
        per = format((100.0 * qty_to_consider * asset_price) / sum_bal, ".2f")
        profit = (asset_price - entry_price) * qty_to_consider
        per_change_r = 0.0
        if profit == 0:
            per_change = 0
        else:
            if _type in ["usdt", "busd"]:
                log(format(abs(profit), ".2f"), "bold green" if profit > 0 else "bold red", end="")
            else:
                _usd = format(abs(profit) * cfg.PRICES["BTCUSDT"], ".2f")
                if profit < 0:
                    _usd = f"-{_usd}"

                log(f"{_usd}$", "green on black blink" if profit > 0 else "red on black blink", end="")
                log(f" {format(abs(profit) * 1000, '.4f')}", "italic green" if profit > 0 else "italic red", end="")

            per_change = percent_change(
                initial=entry_price, change=asset_price - entry_price, end="", is_arrow=False, is_sign=False
            )
            if per_change > 200:
                raise Exception(f"per_change={per_change} is too large; qty of the entry price is calculated wrong")

            if float(per_change) < -10.0:
                per_change_r = percent_change(
                    initial=asset_price, change=entry_price - asset_price, end="", is_arrow=False, color="orange1"
                )
                per_change_r = float(format(per_change_r, ".2f"))

        c = "yellow on black blink"
        if _type in ["usdt", "busd"]:
            current = None
            if profit < 0:
                current = format(_sum + profit, ".2f")
                log(
                    f"[{c}]{per}%[/{c}] | [white on black blink]{current}[/white on black blink] [italic magenta]{format(_sum, '.2f')}",
                    end="",
                )
            else:
                log(f"[{c}]{per}%[/{c}] [italic magenta]{format(_sum, '.2f')}", end="")
        else:
            if float(per) > 0:
                if float(per) > 5:
                    if float(per) >= 100:
                        per = "100"
                    else:
                        per = int(round(float(per)))
                else:
                    per = float(per)

                log(f"[{c}]{per}%[/{c}] ", end="")

            log(f"[italic magenta]{format(_sum * 1000, '.4f')}", end="")

        cfg.locked_balance += float(per)
        if _type in ["usdt", "busd"]:
            msg = f"**{asset}** {entry_price} p={asset_price} q={qty_str} "
        else:
            _entry_price = format(entry_price * 1000, ".4f").strip("0")
            _price = format(asset_price * 1000, ".4f").strip("0")
            msg = f"**{asset}** {_entry_price} p={_price} q={qty_str} "

        per_change_str = format(per_change, ".2f")
        if _type in ["usdt", "busd"]:
            if per_change_r == 0:
                msg = f"{msg}`{format(profit, '.1f')}` ({per_change_str}%) `{round(_sum)}$`\n"
            else:
                msg = f"{msg}`{format(profit, '.1f')}` ({per_change_str}% ↑ {per_change_r}%) `{round(_sum)}$`\n"
        else:
            if per_change_r == 0:
                msg = f"{msg}`{format(profit * 1000, '.5')}` ({per_change_str}%) | {per}% \n"
            else:
                msg = f"{msg}`{format(profit * 1000, '.5')}` ({per_change_str}% ↑ {per_change_r}%) | {per}% \n"

        if _type == "btc":
            _sum = _sum * cfg.PRICES["BTCUSDT"]  # total usdt if type is btc will be used for addition check

        if self.channel:
            if len(cfg.discord_message_full) == 11 and _type in ["usdt", "busd"]:
                special_char = ""
                if config.btc_wavetrend["30m"] == "green":
                    special_char = "+"
                elif config.btc_wavetrend["30m"] == "red":
                    special_char = "-"
                else:
                    special_char = ""

                if config.btc_wavetrend["30m"] != "none":
                    cfg.discord_message_full = cfg.discord_message_full.replace("\n", " ")
                    cfg.discord_message_full += (
                        f"```diff\n{special_char} wt_30m=[  {config.btc_wavetrend['30m'].upper()}  ]\n```"
                    )

            cfg.discord_message_full += msg
            if _type in ["usdt", "busd"] and _sum > config.discord_msg_above_usdt and profit < 0:
                cfg.discord_message += msg
            elif _type == "btc":
                cfg.discord_message += msg

        # self.is_cut_loss(asset, profit, qty_to_consider)
        config.reload_wavetrend()
        if asset in config.SPOT_IGNORE_LIST:
            log()
            return profit
        elif (_type in ["usdt", "busd"] and config.env[_type].status["free"] < 15) or (
            _type == "btc" and float(config.env["btc"].status["free"]) < 0.0003
        ):
            log()
        elif (
            not await self.check_position_to_pass(asset, _sum, is_limit, per)
            and per_change <= -2
            and per_change <= config.env[_type].percent_change_to_add
            and config.btc_wavetrend["30m"] == "green"  # wait until wt for btc is green in 30m
        ):
            await self.add_to_position(asset, qty_to_consider, asset_price, sum_bal, limit_price)

        # if config.btc_wavetrend["30m"] == "red":
        #     log("PASS: btc_wavetrend is red nothing to do", "red")

        await self.is_limit_order_exist(asset, limit_price)
        return profit
