#!/usr/bin/env python3

from contextlib import suppress
from typing import Tuple

from broker._utils._log import log
from broker._utils.tools import decimal_count, percent_change, remove_trailing_zeros, round_float
from broker.errors import QuietExit

from bot import cfg
from bot import config as helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.config import config


class BotHelperSpotAsync(BotHelperAsync):
    def __init__(self) -> None:
        self.channel = None
        self.channel_log = None
        self.channel_alerts = None

    async def check_position_to_pass(self, asset, _sum, is_limit, per) -> bool:
        if _sum > config.isolated_wallet_limit:
            log("pass_a")
            return True

        if float(per) > 80:
            log("pass_b")
            return True

        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            log("pass_c")
            return True

        return False

    async def is_limit_order_exist(self, asset, limit_price) -> None:
        # TODO: cancel only sell positions or update it , keep buy orders
        market = cfg.TYPE.upper()
        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/{market}")
        if open_orders:
            for order in open_orders:
                if order["info"]["side"] == "SELL":
                    if float(limit_price) < float(order["price"]) or cfg.BALANCES[asset]["total"] > float(
                        order["amount"]
                    ):
                        if cfg.BALANCES[asset]["total"] - order["amount"] == 0:
                            await self.new_limit_order(asset, limit_price, market)
                        else:
                            q_per_change = abs(
                                percent_change(
                                    cfg.BALANCES[asset]["total"],
                                    cfg.BALANCES[asset]["total"] - order["amount"],
                                    is_print=False,
                                )
                            )
                            #            94.561                         94.5
                            # # TODO: order["amount"] ile ayni digit sayisi olmali cfg.BALANCES[asset]["total"] kontrol et
                            # if decimal_count(order["amount"]) == 1:
                            #     per_change_delta = 0.1  # prevent 0.1% wrong quantity calculations
                            # else:
                            #     per_change_delta = 0.02  # prevent 0.02% wrong quantity calculations
                            per_change_delta = 0.1
                            if q_per_change == 0 or q_per_change > per_change_delta:
                                # TODO: arta kalan bakiye kucuk alimda isi bozuyor
                                log(f"per_change_delta: {q_per_change} ?= {per_change_delta}")
                                # Note that `q_per_change` may end up 0, which prevent new order to be created
                                await self.new_limit_order(asset, limit_price, market)
        elif not config.env[cfg.TYPE].is_manual_trade:
            await self.new_limit_order(asset, limit_price, market)

    def get_decimal_count(self, symbol, value) -> int:
        try:
            return helper.exchange.spot_markets[symbol]["precision"]["price"]
        except:
            return decimal_count(value)

    def calculate_entry(self, timestamp_list, ordering, trades, asset, asset_qty) -> Tuple[float, float]:
        """Calculates entry price for the position."""
        verbose = False
        _sum = 0.0
        quantity = 0.0
        quantity_real = 0
        quantity_consider_sold = 0.0
        first_sell_flag = False
        latest_buy_trade_idx = 0
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = trades[inner_index]
                if verbose:
                    t = trade.copy()
                    del t["info"]
                    del t["fees"]
                    del t["fee"]
                    del t["takerOrMaker"]
                    del t["type"]
                    log(t)

                if float(trade["info"]["commission"]) > 0 or (
                    float(trade["info"]["commission"]) == 0 and trade["info"]["isMaker"] is True
                ):
                    qty = float(trade["info"]["qty"])
                    if trade["info"]["isBuyer"]:
                        quantity += qty
                        quantity_real += qty
                        quantity_consider_sold += qty
                        _sum += trade["cost"]
                        latest_buy_trade_idx = inner_index
                        latest_ts = trade["timestamp"]
                    else:
                        quantity_real -= qty
                        quantity_consider_sold -= qty
                        if not first_sell_flag and quantity == asset_qty:
                            # latest trade is buyer and equat to current asset number
                            _trade = trades[latest_buy_trade_idx]
                            latest_ts = _trade["timestamp"]
                            if latest_ts != 0:
                                # TODO: in 10 seconds if ts not updated entry calculated wrong
                                # and the gain may added && maliyet azalmis oluyor
                                #: sets timestamp for the asset
                                if latest_ts != config._env.timestamps["root"][asset]:
                                    config._env.timestamps["root"][asset] = latest_ts

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

                if verbose:
                    log(f"qty={quantity_real}")

        return (quantity, _sum)

    async def is_cut_loss(self, asset, profit, qty) -> None:
        """Close trade with accepted loss."""
        # TODO: profit could be 1% of the all money: for testing 2$ for 300$
        if cfg.TYPE == "usdt" and profit < -2.1:
            symbol = f"{asset}/{cfg.TYPE.upper()}"
            open_orders = await helper.exchange.spot.fetch_open_orders(symbol)
            for order in open_orders:
                with suppress(Exception):
                    # the order may already closed if there was a rapid change
                    await helper.exchange.spot.cancel_order(order["id"], symbol)

            order = await helper.exchange.spot.create_market_sell_order(symbol, qty)
            order = order["info"]
            with suppress(Exception):
                for k in ["timeInForce", "orderListId", "price", "status", "type", "origQty", "executedQty"]:
                    del order[k]

            log(f"==> CUT LOSS for {asset}={profit}", "bold blue")
            log(order)

    async def add_to_position(self, asset, qty, asset_price, sum_bal, limit_price) -> None:
        new_qty = qty * config.env[cfg.TYPE].multiply_ratio
        if new_qty * asset_price < 10:
            # usdt_multiply_ratio should be 0.1; minimum order should be more than 10$
            new_qty = qty * 1.05

        per = (100.0 * new_qty * asset_price) / sum_bal
        log(f"==> new_order_qty={new_qty} | [cy]%{format(float(per), '.2f')}[/cy] of the total asset")
        order = await self.spot_order(new_qty, f"{asset}/{cfg.TYPE.upper()}", "BUY")
        if order:
            order = order["info"]
            for item in cfg.order_del_list + ["fills"]:
                with suppress(Exception):
                    del order[item]

            log(f"market_order={order}")
            await self.new_limit_order(asset, limit_price, cfg.TYPE.upper())

    def ll(self, value):
        if cfg.TYPE in ["usdt", "busd"]:
            return value
        else:
            return format(float(value) * 1000, ".5f")

    async def _spot_check_target_order(self, asset, _sum, is_limit):
        balance = cfg.BALANCES[asset]["total"]
        if balance > 0 and asset != "DUMMY":  # TODO: asset in PASS or ignore
            try:
                # TODO: takes long time, try to make is faster!!
                output = await self.spot_check_target_order(asset, balance, _sum, is_limit)
                if cfg.TYPE == "btc" and "change_type" in config.cfg["root"][cfg.TYPE]:
                    if asset in config.cfg["root"][cfg.TYPE]["change_type"]:
                        output = output / cfg.PRICES["BTCUSDT"]

                self.lost += float(output)
            except Exception as e:
                log(e)
        else:
            log(f"{asset} balance is zero")

    async def spot_check_target_order(self, asset, asset_qty, sum_bal, is_limit=True) -> float:
        """Give limit order on the spot market.

        :param asset_qty: complete quantity of the asset, could be left over due the 0 BNB

        __ https://stackoverflow.com/questions/70318352/how-to-get-the-price-of-a-crypto-at-a-given-time-in-the-past
        """
        # TODO: maybe could be done in thread to make the process much much faster
        _type = cfg.TYPE
        symbol: str = f"{asset}/{_type.upper()}"
        since = await config.get_spot_timestamp(asset, symbol)
        if len(str(since)) == 10:
            since = since * 1000

        decimal: int = 8
        try:
            decimal = helper.exchange.spot_markets[symbol]["precision"]["price"]  # TODO: store at PRICES
        except Exception as e:
            if "/USDT" in symbol:
                symbol = symbol.replace("/USDT", "/BUSD")
                decimal = helper.exchange.spot_markets[symbol]["precision"]["price"]
            else:
                raise e

        if "change_type" in config.cfg["root"][cfg.TYPE]:
            if asset in config.cfg["root"][cfg.TYPE]["change_type"]:
                _type = "usdt"

        # for _asset in config.cfg["root"][cfg.TYPE]["entry_prices"]:
        #     if  == _asset:
        #         _type = "usdt"
        #         entry_price = config.cfg["root"][cfg.TYPE]["entry_prices"][asset]
        #         qty_to_consider = asset_qty
        #         _sum = float(entry_price) * asset_qty
        #     elif f"{asset}BTC" == _asset:
        #         _type = "btc"

        if asset in config.cfg["root"][cfg.TYPE]["entry_prices"]:
            entry_price = config.cfg["root"][cfg.TYPE]["entry_prices"][asset]
            qty_to_consider_locked_per = qty_to_consider = asset_qty
            _sum = float(entry_price) * asset_qty
        else:
            trades = await helper.exchange.spot.fetch_my_trades(symbol, since=since)
            timestamp_list = None
            if trades:
                """
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
                """
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
                latest_busd_ts = 0
                with suppress(Exception):
                    if "/USDT" in symbol:
                        trades_busd = await helper.exchange.spot.fetch_my_trades(symbol.replace("/USDT", "/BUSD"))
                        ordering_busd = {}
                        for idx, trade in enumerate(trades_busd):
                            try:
                                ordering_busd[trade["timestamp"]].append(idx)
                            except Exception:
                                ordering_busd[trade["timestamp"]] = [idx]

                        timestamp_list_busd = sorted(ordering_busd, reverse=True)
                        latest_busd_ts = timestamp_list_busd[0]

                try:
                    if timestamp_list[0] > latest_busd_ts:
                        qty, _sum = self.calculate_entry(timestamp_list, ordering, trades, asset, asset_qty)
                    else:
                        qty, _sum = self.calculate_entry(
                            timestamp_list_busd, ordering_busd, trades_busd, asset, asset_qty
                        )
                except Exception as e:
                    log(f"warning: [  {asset}{_type.upper()}  ] {e}")
                    return 0

            if asset_qty == 0:
                log(f"E: float division by zero asset={asset}")
                return 0

            if qty == 0:
                return 0

            if (
                abs(float(asset_qty) - float(qty)) > 0.000000000001
                and asset not in config.cfg["root"][cfg.TYPE]["entry_prices"]
                and asset not in config.cfg["root"]["ignore_warning"]
            ):
                # TODO: qty + remaining amount // there could be left over # 84.4262 != 84.4 | left_over: 0.0262
                log(f"wrong calculation for {symbol} {asset_qty} != {qty}", is_write=False)

            qty_to_consider = qty
            if asset_qty > qty:
                #: could be additional gain from the margin trading.
                qty_to_consider = asset_qty

            # TODO: CHECKME
            qty_to_consider_locked_per = asset_qty
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

        if entry_price == limit_price:
            log(f"** {asset} q={qty_str} e={self.ll(entry_price)} ", "b", end="")  # entry price
            raise Exception(f"entry_price and limit_price are same and equal to {entry_price}")

        if asset == "BTTC":
            # here price is fetched from BTTCTRY pair since its more correct
            asset_price = await self.spot_fetch_ticker(f"{asset}TRY")
            USDTTRY = await self.spot_fetch_ticker("USDTTRY")
            cfg.PRICES[asset] = asset_price = float(format(asset_price / USDTTRY, ".10f"))
        else:
            asset_price = await self.spot_fetch_ticker(f"{asset}{_type.upper()}")

        log(f"** {asset} {self.ll(asset_price)} e={self.ll(entry_price)} ", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"t={self.ll(limit_price)} ", end="")  # prints the target price

        log(f"q={qty_str} ", end="")
        per = format((100.0 * qty_to_consider * asset_price) / sum_bal, ".2f")
        per_locked = format((100.0 * qty_to_consider_locked_per * asset_price) / sum_bal, ".2f")
        profit = (asset_price - entry_price) * qty_to_consider
        per_change_r = 0.0
        if profit == 0:
            per_change = 0
        else:
            per_change = percent_change(
                initial=entry_price, change=asset_price - entry_price, end="", is_arrow=False, is_sign=False
            )
            if _type in ["usdt", "busd"]:
                log(format(abs(profit), ".2f"), "green" if profit > 0 else "red", end="")
                log(" ", end="")
            else:
                _usd = format(abs(profit) * cfg.PRICES["BTCUSDT"], ".2f")
                if profit < 0:
                    _usd = f"-{_usd}"
                elif _usd == "0.00":  # float(_usd) == 0
                    _usd = format(abs(profit) * cfg.PRICES["BTCUSDT"], ".3f")

                log(f"${_usd}", "green on black blink" if profit > 0 else "red on black blink", end="")
                log(f" {format(abs(profit) * 1000, '.2f')} ", "italic green" if profit > 0 else "italic red", end="")
            if asset not in config.SPOT_IGNORE_LIST and per_change > 20:
                cfg.FIRST_PRINT_CYCLE = False
                if cfg.ENTRY_PRICE_VERBOSE:
                    msg = f"per_change={per_change} is too large; qty of the entry price is calculated wrong"
                    raise Exception(msg)
                else:
                    raise QuietExit(f"per_change={int(per_change)} is too large")

            if float(per_change) < -10:
                per_change_r = percent_change(
                    initial=asset_price, change=entry_price - asset_price, end="", is_arrow=False, color="orange1"
                )
                per_change_r = float(format(per_change_r, ".2f"))

        current_sum = format(_sum + profit, ".2f")
        c = "yellow on black blink"
        if _type in ["usdt", "busd"]:
            if profit < 0:
                c1 = "white on black blink"
            else:
                c1 = "green on black blink"

            if float(per_locked) == int(float(per_locked.replace(".00", ""))):
                per_locked = str(int(float(per_locked.replace(".00", ""))))

            if float(per_locked) > 150:
                log(f"| [{c1}]{current_sum}[/{c1}] [ib]{format(_sum, '.2f')} ", end="")
            else:
                log(f"[{c}]{per_locked}%[/{c}] | [{c1}]{current_sum}[/{c1}] [ib]{format(_sum, '.2f')} ", end="")
        else:
            if float(per_locked) > 0:
                if float(per_locked) > 5:
                    if float(per_locked) >= 100:
                        per_locked = "100"
                    else:
                        per_locked = str(int(round(float(per_locked))))
                else:
                    per_locked = str(float(per))

                log(f"[{c}]{per}%[/{c}] ", end="")

            log(format(_sum * 1000, ".4f"), "ib", h=False)

        real_pos_count = config._env._status.find_one("real_pos_count")["value"]
        if _type in ["usdt", "busd"] and real_pos_count > 0:
            log()  # newline

        if cfg.TYPE == "btc":
            if "change_type" in config.cfg["root"][cfg.TYPE] and asset in config.cfg["root"][cfg.TYPE]["change_type"]:
                cfg.locked_balance += 0.1
                # pass
            else:
                cfg.locked_balance += float(per_locked)
        else:
            cfg.locked_balance += float(per_locked)

        if _type in ["usdt", "busd"]:
            msg = f"**{asset}** {entry_price} p={asset_price} q={qty_str} "
        else:
            _entry_price = format(entry_price * 1000, ".5f").replace("0.", "").lstrip("0")
            _price = format(asset_price * 1000, ".5f").replace("0.", "").lstrip("0")
            msg = f"**{asset}** {_entry_price} p={_price} q={qty_str} "

        per_change_str = format(per_change, ".2f")
        if _type in ["usdt", "busd"]:
            if per_change_r == 0:
                msg = f"{msg}`{format(profit, '.2f')}` ({per_change_str}%) `{current_sum}$`"
            else:
                msg = f"{msg}`{format(profit, '.2f')}` ({per_change_str}% **↑**{per_change_r}%) `{current_sum}$`"
        else:
            if per_change_r == 0:
                msg = f"{msg}`{format(profit * 1000, '.5')}` ({per_change_str}%) | {per}%"
            else:
                msg = f"{msg}`{format(profit * 1000, '.5')}` ({per_change_str}% **↑**{per_change_r}%) | {per}%"

        msg = f"{msg}\n"
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
            if _type in ["usdt", "busd"]:
                cfg.discord_message += msg
            elif _type == "btc":
                cfg.discord_message += msg

        if config.env[_type].is_manual_trade:  # manual trade is on
            return profit

        await self.is_cut_loss(asset, profit, qty_to_consider)
        config.reload_wavetrend()
        if asset in config.SPOT_IGNORE_LIST:
            # log()
            return profit

        if (_type in ["usdt", "busd"] and config.env[_type].status["free"] < 15) or (
            _type == "btc" and float(config.env["btc"].status["free"]) < 0.0003
        ):
            pass  # log()
        elif (
            profit < 0
            and per_change <= -2
            and per_change <= config.env[_type].percent_change_to_add
            and not await self.check_position_to_pass(asset, _sum, is_limit, per)
        ):
            if config.env[_type].stop_trade_wt_30m_red:
                if config.btc_wavetrend["30m"] == "green":
                    #: wait until wt for btc is green in 30m
                    await self.add_to_position(asset, qty_to_consider, asset_price, sum_bal, limit_price)
            else:
                await self.add_to_position(asset, qty_to_consider, asset_price, sum_bal, limit_price)

        # if config.btc_wavetrend["30m"] == "red":
        #     log("PASS: btc_wavetrend is red nothing to do", "red")

        await self.is_limit_order_exist(asset, limit_price)
        return profit
