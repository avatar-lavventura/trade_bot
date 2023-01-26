#!/usr/bin/env python3

import os
import sys
from contextlib import suppress
from typing import Tuple

from broker._utils._log import console_ruler, log
from broker._utils.tools import _date, decimal_count, print_tb

from bot import cfg
from bot.config import config, exchange, is_start
from bot.fund_time import Fund
from bot.take_profit import TakeProfit

TP = TakeProfit()
fund = Fund()


class BotHelperAsync:
    async def close(self):
        """Close the async function.

        __ https://stackoverflow.com/a/54528397/2402577
        """
        await exchange.close()

    def _update_timestamp_status(self, key) -> None:
        #: ts when iteration started
        latest_ts = config.env[cfg.TYPE].status["timestamp"]
        config.env[cfg.TYPE]._ts.add_single_key("latest", latest_ts)
        del_list = []
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp not in config.asset_list:
                ts = int(config.timestamp[key][asset_timestamp])
                if len(str(ts)) == 13 and ts <= latest_ts * 1000:
                    del_list.append(asset_timestamp)
                elif ts <= latest_ts:
                    del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

    def update_timestamp_status(self) -> None:
        self._update_timestamp_status(f"{cfg.TYPE}_timestamp")
        # if cfg.TYPE == "usdt" and config.cfg["root"]["busd"]["status"] == "on":
        #     self._update_timestamp_status("busd_timestamp")

    async def fetch_symbol_percent_change(self, symbol, price=None):
        bar_price = fund.percent_change_since_day_start(symbol)
        try:
            bar_price = bar_price[0][1]  # time, open, high, low, close, volume
        except Exception as e:
            raise KeyboardInterrupt from e

        if price:
            asset_price = price
        else:
            asset_price = await self.spot_fetch_ticker(symbol)

        percent = ((asset_price - bar_price) / bar_price) * 100
        return asset_price, float(format(percent, ".2f"))

    async def analyze_positions(self, name, lost, pos_count, free, total) -> None:
        c = "red" if float(lost) < 0 < float(cfg.locked_balance) else "green"
        msg = ""
        lost = float(lost)
        real_pos_count = config.env[cfg.TYPE]._status.find_one("real_pos_count")["value"]
        if name == "mBTC":
            msg += "-=-=-=-=-=-= "
            if lost != 0:
                lost_usdt = lost / 1000 * cfg.PRICES["BTCUSDT"]
                msg += f"[{c}]{format(lost_usdt, '.2f')}$({lost})[/{c}] "

            msg += f"locked=[cy]{format(float(cfg.locked_balance), '.2f')}%[/cy] "
            if free > 0:
                _free_usdt = float(free) * cfg.PRICES["BTCUSDT"]
                free = format(free * 1000, ".4f")
                msg = f"{msg}free_btc=[cy]{free}[/cy]([cy]{format(_free_usdt, '.2f')}$[/cy]) "

            _total = cfg.SUM_BTC + abs(lost) / 1000
            _total = format(_total, ".5f")
            msg += f"[italic black]{_total}[/italic black]"
        else:
            msg += "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= "
            # total_str = f"[italic #6272a4]{total}[/italic #6272a4]"
            msg += f"[{c}]{abs(lost)}{name}[/{c}] locked=[cy]{cfg.locked_balance}%[/cy] "
            if free > 1:
                msg = f"{msg}free=[cy]{free}{name}[/cy] "

        if float(cfg.locked_balance) > 0:
            if real_pos_count > 1:
                log(msg, "bold", end="")
            else:
                log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=", "bold", end="")

            output = config.env[cfg.TYPE].stats.find_one(cfg.CURRENT_DATE)
            if pos_count > 2:
                if output:
                    log(f"pos=[blue]{pos_count}[/blue] perf=[blue]{output['value']}[/blue]", "bold")
                else:
                    log(f"pos=[blue]{pos_count}[/blue]", "bold")
            elif output:
                log(f"perf=[blue]{output['value']}[/blue]", "bold")
            else:
                log()

    async def restart(self):
        log()
        log(f"#> -=-=-=-=-=-=-=-=-=- [green]RESTARTING[/green] {_date()}-=-=-=-=-=-=-=-=-=- [blue]<#", is_write=False)
        os.execv(sys.argv[0], sys.argv)

    async def _discord_sent_msg(self, msg):
        try:
            if cfg.discord_sent_msg:
                await cfg.discord_sent_msg.edit(content=msg)
            else:
                cfg.discord_sent_msg = await self.channel.send(msg)
        except Exception as e:
            log(f"E: discord: {e}")
            # if "Not Found" not in str(e) and "HTTPException" not in str(e):
            #     print_tb(e)

            if "Service Unavailable" in str(e):
                self.restart()

            with suppress(Exception):
                await cfg.discord_sent_msg.delete()

            cfg.discord_message = f"`{_date()}`\n"
            cfg.discord_sent_msg = None

    async def _discord_send_watchlist(self) -> None:
        msg = ""
        flag = False
        for symbol in config.WATCHLIST:
            if not flag:
                flag = True
                msg = f"{msg}\n```"

            try:
                asset_price, percent = await self.fetch_symbol_percent_change(symbol)
            except Exception as e:
                log(f"E: {symbol} {e}")
                print_tb(e)

            per_str = f"({percent}%)" if percent < 0 else f"(+{percent}%)"
            if symbol == "BTCUSDT":
                asset_price = "{:,}".format(int(asset_price)).replace(",", ".")
            elif "BTC" in symbol:
                asset_price = "{:.8f}".format(asset_price).lstrip("0.")  # .rstrip("0")

            msg = f"{msg}\n{symbol}={asset_price} {per_str}"

        if msg:
            _da = _date(_type="hour")
            if _da[0:5] == "03:00":
                _da = _date()

            msg = f"{msg}\n```{_da}  ${config.estimated_balance()}"
            await self._discord_sent_msg(msg)

    async def _discord_send(self, msg, lost, pos_count, name, free, total, is_message=True) -> None:
        cfg.locked_balance = 100 if float(cfg.locked_balance) > 99.4 else format(cfg.locked_balance, ".2f")
        await self.analyze_positions(name.replace(" ", ""), lost, pos_count, free, total)
        if not is_message:
            return

        if (
            cfg.discord_message
            and len(cfg.discord_message) > 11
            or (cfg.TYPE == "btc" and cfg.discord_message_full and len(cfg.discord_message_full) >= 11)
        ):
            if cfg.TYPE == "usdt":
                flag = False
                for symbol in config.WATCHLIST:
                    if not flag:
                        flag = True
                        msg = f"{msg}\n```"

                    try:
                        asset_price, percent = await self.fetch_symbol_percent_change(symbol)
                    except Exception as e:
                        log(f"E: {symbol} {e}")
                        print_tb(e)

                    per_str = f"({percent}%)" if percent < 0 else f"(+{percent}%)"
                    if symbol == "BTCUSDT":
                        if percent == 0:
                            per_str_c = "(0.0%)"
                        else:
                            per_str_c = f"([red]{percent}%[/red])" if percent < 0 else f"([green]+{percent}%[/green])"

                        asset_price = "{:,}".format(int(asset_price)).replace(",", ".")
                        if symbol == "BTCUSDT":
                            c = "m"
                        else:
                            c = "cy"

                        log(f" * {symbol}=[{c}]{asset_price}[/{c}] {per_str_c}", end="", is_write=False)
                    elif "BTC" in symbol:
                        asset_price = "{:.8f}".format(asset_price).lstrip("0.")  # .rstrip("0")

                    msg = f"{msg}\n{symbol}={asset_price} {per_str}"
                if flag:
                    msg = f"{msg}\n```"

            await self._discord_sent_msg(msg)

    ########
    # SPOT #
    ########
    async def _fetch_margin_balance(self):
        """Fetch margin balance.

        Example output:
        ipdb> balances["info"]["assets"][0]["quoteAsset"] {'asset': 'USDT',
        'borrowEnabled': True, 'borrowed': '0', 'free': '2.1602058', 'interest':
        '0', 'locked': '0', 'netAsset': '2.1602058', 'netAssetOfBtc':
        '0.0001003', 'repayEnabled': True, 'totalAsset': '2.1602058'}
        """
        balances = await exchange.margin_isolated.fetch_balance()
        total_asset = balances["info"]["assets"][0]["quoteAsset"]["totalAsset"]
        return total_asset

    async def _fetch_balance(self) -> None:
        pos_count = 0
        real_pos_count = 0
        ongoing_positions = []
        cfg.BALANCES = await exchange.spot.fetch_balance()
        for symbol in cfg.BALANCES:
            if symbol not in cfg.ignore_list and cfg.BALANCES[symbol]["total"] > 0:
                ongoing_positions.append(symbol)
                if symbol not in cfg.STABLE_COINS:
                    real_pos_count += 1
                    if symbol not in config.SPOT_IGNORE_LIST:
                        pos_count += 1

        del_list = []
        key = f"{cfg.TYPE}_timestamp"
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp != "base" and asset_timestamp not in ongoing_positions:
                del_list.append(asset_timestamp)

        for asset in del_list:
            del config.timestamp[key][asset]

        config.env[cfg.TYPE]._status.add_single_key("count", pos_count)
        config.env[cfg.TYPE]._status.add_single_key("real_pos_count", real_pos_count)

    async def spot_balance(self, is_limit=True) -> Tuple[float, float, float, float]:
        """Calculate USDT balance in spot."""
        own_usdt: float = 0
        sum_usdt: float = 0
        sum_busd: float = 0
        sum_btc: float = 0
        only_usdt: float = 0
        only_btc: float = 0
        count: int = 0
        config.asset_list = []
        try:
            await self._fetch_balance()
        except Exception as e:
            if "Account has insufficient balance" in e:
                log("", is_write=False)

            log(f"E: {e}", is_write=False)

        for balance in cfg.BALANCES["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0 or float(balance["locked"]) != 0:
                quantity = float(balance["free"]) + float(balance["locked"])
                if asset == "BTC":
                    only_btc = quantity
                    sum_btc += quantity
                elif asset not in cfg.STABLE_COINS:
                    price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")
                    if cfg.TYPE == "usdt":
                        usdt_amount = quantity * float(price)
                        if usdt_amount > 1.0:  # below 1.0$ would not be count as open position
                            config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1
                    elif cfg.TYPE == "btc":
                        sum_btc += quantity * float(price)
                        usdt_amount = quantity * float(price) * cfg.PRICES["BTCUSDT"]
                        if usdt_amount > 1:
                            config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1

                    sum_usdt += usdt_amount
                elif asset.lower() == cfg.TYPE:
                    only_usdt = quantity
                    sum_usdt += quantity
                elif asset.lower() == "busd":
                    sum_busd += quantity
                if asset.lower() == "bnb":
                    cfg.BNB_QTY = quantity
                    cfg.BNB_BALANCE = quantity * await self.spot_fetch_ticker("BNBUSDT")

        ts = config.env[cfg.TYPE].status["timestamp"]
        own_usdt = sum_btc * cfg.PRICES["BTCUSDT"]
        pos_count: int = config.env[cfg.TYPE]._status.find_one("count")["value"]
        if sum_btc > 0.00002 and pos_count > 0:
            log(
                f" * btc=[m]%.8f[/m] [blue]==[/blue] [m]%.2f$[/m] [blue]*[/blue] "
                f"bnb=[cy]%.2f$[/cy] | [blue]{_date(_type='hour')}[/blue] {ts}" % (sum_btc, own_usdt, cfg.BNB_BALANCE)
            )
            cfg.SUM_BTC = sum_btc

        if cfg.BNB_BALANCE < 0.3:
            try:
                await self.buy_bnb()
            except Exception as e:
                if "InsufficientFunds" in str(e) or "insufficient balance" in str(e):
                    log(f"E: {e}")
                else:
                    print_tb(e)

        sum_usdt = float(format(sum_usdt, ".2f"))
        sum_busd = float(format(sum_busd, ".2f"))
        if is_start:
            if not is_start and sum_usdt > 0.01:
                console_ruler(character="-=")

            if len(config.asset_list) == 0 or config.trade_mode:
                config.timestamp[f"{cfg.TYPE}_timestamp"] = {}  #: cleans timestamp.yaml file
                _da = f"[blue]{_date(_type='hour')}[/blue]"
                _sum_usdt = format(sum_usdt, ".2f")
                if cfg.TYPE == "usdt":
                    #: estimated balance:
                    _total_balance = format(float(_sum_usdt) + float(sum_busd), ".2f")
                    log(f":heavy_dollar_sign: [cy]${_total_balance}[/cy] | {_da}", "bold")
                    config.env[cfg.TYPE].estimated_balance.add_single_key("total_balance", _total_balance)
                elif cfg.TYPE == "btc":
                    if own_usdt > 0.01:
                        #: estimated balance:
                        _total_balance = format(own_usdt + sum_busd, ".2f")
                        log(":bee: ", end="")
                        if only_btc > 0:
                            log(f"btc={only_btc} ", "bold", end="")

                        if sum_busd > 0.1:
                            log(f"busd={sum_busd} | ", "bold", end="")

                        log(
                            "%.8f BTC[blue] ≈[/blue] [cy]$%.2f[/cy] " % (sum_btc, own_usdt),
                            "bold",
                            end="",
                        )
                        log(f"| {_da}", "bold")
                        config.env[cfg.TYPE].estimated_balance.add_single_key("total_balance", _total_balance)
                    else:
                        log(f":bee: {_date(_type='hour')} spot_balance=0", "bold")
            elif cfg.TYPE == "usdt":
                busd_str = ""
                if sum_busd > 0.1:
                    busd_str = f"| busd={sum_busd} "

                log(
                    f" * usdt={_sum_usdt} {busd_str}[blue]*[/blue] "
                    f"bnb=[cy]{format(cfg.BNB_BALANCE, '.2f')}$[/cy] | {_da} {ts}"
                )

            config.sum_usdt = sum_usdt
            if sum_usdt > 1.0:
                if pos_count == 0 and config.env[cfg.TYPE].status["balance"] != sum_usdt:
                    config.env[cfg.TYPE].status["balance"] = sum_usdt

            if cfg.TYPE == "btc":
                config.env[cfg.TYPE].status["balance"] = float(format(sum_btc, ".8f"))

        if cfg.TYPE == "usdt":
            _sum = sum_usdt
        else:
            _sum = sum_btc

        lost: float = 0
        cfg.locked_balance = 0.0
        cfg.discord_message = f"`{_date()}`\n"
        cfg.discord_message_full = f"`{_date()}`\n"
        if cfg.BALANCES:
            new_asset_list = []  # TODO: order asset based on their position size sort the list based on its size
            for asset in config.asset_list:
                balance = cfg.BALANCES[asset]["total"]
                if balance > 0:
                    new_asset_list.append(asset)

            for asset in config.asset_list:
                balance = cfg.BALANCES[asset]["total"]
                if balance > 0:
                    output = await self.spot_limit(asset, balance, _sum, is_limit)
                    lost += float(output)
                else:
                    log(f"{asset} balance is zero")
        else:
            for asset in config.asset_list:
                output = await self.spot_limit(asset, config.btc_quantity[asset], _sum, is_limit)
                lost += float(output)

        if cfg.TYPE == "usdt":
            free = format(float(config.env["usdt"].status["free"]), ".2f")
            if lost > -5.0:
                _msg = cfg.discord_message
            else:
                _msg = cfg.discord_message_full
        else:
            free = format(float(config.env["btc"].status["free"]), ".5f")
            if lost > -0.0001:
                _msg = cfg.discord_message
            else:
                _msg = cfg.discord_message_full

        cfg.locked_balance = min(float(cfg.locked_balance), 100)
        if cfg.locked_balance >= 99.90:
            cfg.locked_balance = 100
            locked_per = ":lock:=`100%`"
        else:
            locked_per = f":lock:=`{format(cfg.locked_balance, '.2f')}%`"

        pos_str = ""
        if pos_count > 2:
            pos_str = f"pos=**{pos_count}**"
        elif config.trade_mode:
            log()  # needed to not overwrite printed balance

        total = 0
        free = float(free)
        if cfg.TYPE == "usdt":
            _free = ""
            if free > 1:
                _free = f"| free=`{free}` "

            total = round(abs(lost) + sum_usdt)
            if sum_busd > 0.1:
                msg = (
                    f"{_msg}`{format(lost, '.2f')}$` usdt=`{round(sum_usdt)}` | busd=`{sum_busd}` {_free}"
                    f"{locked_per} | {pos_str}"
                )
            else:
                goal = round(float(sum_usdt) + float(abs(lost)))
                msg = (
                    f"{_msg}**:moneybag:=`{round(sum_usdt)}` lost=**`{format(lost, '.2f')}` :dart:=`{goal}` {_free}"
                    f"{locked_per} {pos_str}"
                )

            config.env[cfg.TYPE].balance_sum.add_single_key("btc", 0)
            config.env[cfg.TYPE].balance_sum.add_single_key("usdt", format(sum_usdt, ".2f"))
        else:
            msg = _msg
            if free > 0:
                msg = f"{msg}free=`{free}` (`{format(free * cfg.PRICES['BTCUSDT'], '.2f')}$`) "

            lost_usdt = format(float(lost) * cfg.PRICES["BTCUSDT"], ".2f")
            if float(lost_usdt) < 0:
                msg = (
                    f"{msg}btc=**`{format(sum_btc, '.5f')}`** (**`{format(own_usdt, '.2f')}`:moneybag:**)\n"
                    f"**lost=`{lost_usdt}`** {locked_per} {pos_str}"
                )
            elif float(lost_usdt) == 0:
                msg = f":beer: **`{format(sum_btc, '.5f')}`** BTC == **`{format(own_usdt, '.2f')}`:moneybag:** @binance_{cfg.TYPE}"
            else:
                msg = (
                    f"{msg}btc=**`{format(sum_btc, '.5f')}`** (**`{format(own_usdt, '.2f')}`:moneybag:**)\n"
                    f"**gain=`+{lost_usdt}$`** {locked_per} {pos_str}"
                )

            config.env[cfg.TYPE].balance_sum.add_single_key("btc", format(sum_btc, ".8f"))
            config.env[cfg.TYPE].balance_sum.add_single_key("usdt", format(own_usdt, ".2f"))

        output = config.env[cfg.TYPE].stats.find_one(cfg.CURRENT_DATE)
        if output:
            msg = f"{msg} perf=**{output['value']}**"

        if config.cfg["root"][cfg.TYPE]["is_discord"] == "on":
            if cfg.TYPE == "btc":
                await self._discord_send(
                    msg, format(lost * 1000, ".5f"), pos_count, " mBTC", free, total, is_message=True
                )
            else:
                await self._discord_send(msg, format(lost, ".2f"), pos_count, "$", free, total)
        else:
            if cfg.TYPE == "btc":
                await self.analyze_positions("mBTC", format(lost * 1000, ".5f"), pos_count, free, total)
            else:
                await self._discord_send_watchlist()
                await self.analyze_positions("$", format(lost, ".2f"), pos_count, free, total)

        config.env[cfg.TYPE]._status.add_single_key("count", count)
        self.update_timestamp_status()
        return own_usdt, sum_usdt, only_usdt, only_btc

    async def buy_bnb(self) -> bool:
        cfg.BNB_BALANCE = float(format(cfg.BNB_BALANCE, ".6f"))
        if cfg.TYPE == "btc":
            asset = "BNBBTC"
            amount: float = 0.00011
        else:
            asset = "BNBUSDT"
            amount: float = 10.5

        if float(config.env[cfg.TYPE].status["free"]) < amount:
            return False

        log(f"#> buying minimum amount of [green]BNB[/green] bnb_balance={cfg.BNB_BALANCE}", is_write=False, end="")
        output = await self.spot_fetch_ticker(asset)
        order = await exchange.spot.create_market_buy_order(asset, float(format(amount / output, ".3f")))
        log("[  ok  ]", is_write=False)
        order = order["info"]
        with suppress(Exception):
            del order["timeInForce"]
            del order["orderListId"]
            del order["price"]
            del order["status"]
            del order["type"]
            del order["origQty"]
            del order["executedQty"]

        log(order, is_write=False)
        return True

    async def spot_order(self, quantity, symbol, side, is_return=False, from_ex=False):
        if not from_ex:
            log(f"==> market_buy_order_quantity={quantity}")

        try:
            return await exchange.spot.create_market_buy_order(symbol, quantity)
        except Exception as e:
            _e = str(e)
            if "Account has insufficient balance" in _e:
                log("E: Account has insufficient balance for requested action", is_write=False)
                if is_return or from_ex or config.env[cfg.TYPE].status["free"] < cfg.MINIMUM_POSITION[cfg.TYPE] * 4:
                    return

                quantity = quantity / 4  # re-try with much smalleer position size
                log(f"==> re-opening [green]{side}[/green] 1/4_of_quantity={quantity} for {symbol}")
                return await self.spot_order(quantity, symbol, side, is_return=True, from_ex=True)
            elif "Precision is over the maximum defined for this asset" in _e or "Filter failure: LOT_SIZE" in _e:
                log(f"E: {e} qty={quantity}")
                decimal = decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening [green]{side}[/green] order qty={_quantity}")
                if float(_quantity) > 0:
                    return await self.spot_order(_quantity, symbol, side, from_ex=True)
                else:
                    log("E: quantity is zero, nothing to do", is_write=False)
            elif "Filter failure: MIN_NOTIONAL" in _e and quantity >= 0.1:
                quantity += 0.1
                #: fixes if its overrounded, ex: 1.2000000000000002
                quantity = float("{:.1f}".format(quantity))
                log(f"==> re-opening [green]{side}[/green] order qty={quantity}")
                return await self.spot_order(quantity, symbol, side, from_ex=True)
            else:
                print_tb(e)
                raise e

    async def spot_fetch_ticker(self, asset, is_bid_price=False) -> float:
        if not is_bid_price and asset in cfg.PRICES:
            if cfg.PRICES[asset] != 0:
                return cfg.PRICES[asset]

        try:
            price_ticker = await exchange.spot.fetch_ticker(asset)
            if is_bid_price:
                return float(price_ticker["info"]["bidPrice"])

            #: record prices in case could be used in the same cycle
            cfg.PRICES[asset] = price_ticker["last"]
            return float(price_ticker["last"])
        except Exception as e:
            if "binance does not have market symbol" in str(e):
                if "USDT" in asset:
                    asset = asset.replace("USDT", "BUSD")
                    return await self.spot_fetch_ticker(asset, is_bid_price)

            raise e

    async def new_limit_order(self, asset, limit_price, market="BTC"):
        """Create new limit order with the added quantity."""
        symbol = f"{asset}/{market}"
        open_orders = await exchange.spot.fetch_open_orders(symbol)
        for order in open_orders:
            with suppress(Exception):
                # the order may already closed if there was a rapid change
                await exchange.spot.cancel_order(order["id"], symbol)

        try:
            balance = await self.fetch_balance(asset)
            response = await exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
            log("==> [green]new_limit_order[/green]=", end="")
            if "info" in response:
                response = response["info"]

            with suppress(Exception):
                del response["status"]
                del response["clientOrderId"]
                del response["timeInForce"]
                del response["cummulativeQuoteQty"]
                del response["orderListId"]
                del response["executedQty"]
                del response["fills"]

            log(response, "bold cyan")
        except Exception as e:
            if type(e).__name__ != "InvalidOrder":
                log(f"E: Failed to create order with {symbol} [cy]{type(e).__name__}[/cy] {e}")

    async def fetch_balance(self, code) -> float:
        balance = await exchange.spot.fetch_balance()
        return balance[code]["total"]
