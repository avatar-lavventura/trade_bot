#!/usr/bin/env python3

from contextlib import suppress
from typing import Tuple

from broker._utils._log import _console_clear, console_ruler, log
from broker._utils.tools import _date, decimal_count, print_tb

from bot import cfg, helper
from bot.config import config
from bot.fund_time import Fund
from bot.take_profit import TakeProfit

TP = TakeProfit()
fund = Fund()


class BotHelperAsync:
    async def close(self):
        """Close async function.

        __ https://stackoverflow.com/a/54528397/2402577
        """
        await helper.exchange.close()

    def _update_timestamp_status(self, key) -> None:
        del_list = []
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp not in config.asset_list:
                ts = int(config.timestamp[key][asset_timestamp])
                if len(str(ts)) == 13:
                    if ts <= config.env[cfg.TYPE].status["timestamp"] * 1000:
                        del_list.append(asset_timestamp)
                elif ts <= config.env[cfg.TYPE].status["timestamp"]:
                    del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

    def update_timestamp_status(self) -> None:
        self._update_timestamp_status(f"{cfg.TYPE}_timestamp")
        if cfg.TYPE == "usdt" and config.cfg["root"]["busd"]["status"] == "on":
            self._update_timestamp_status("busd_timestamp")

    async def fetch_symbol_percent_change(self, symbol, price=None):
        bar_price = fund.percent_change_since_day_start(symbol)
        try:
            bar_price = bar_price[0][1]  # Time, Open, High, Low, Close, Volume
        except Exception as e:
            raise KeyboardInterrupt from e

        if price:
            asset_price = price
        else:
            asset_price = await self.spot_fetch_ticker(symbol)

        percent = ((asset_price - bar_price) / bar_price) * 100
        return asset_price, float(format(percent, ".2f"))

    async def _discord_send(self, msg, lost, count, name, free, is_message=True) -> None:
        cfg.locked_balance = float(format(cfg.locked_balance, ".2f"))
        cfg.locked_balance = 100 if cfg.locked_balance > 99.5 else cfg.locked_balance
        c = "red" if float(lost) < 0 < cfg.locked_balance else "green"
        log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- ", "gray", end="", fn=cfg.balance_fn)
        if name.replace(" ", "") == "mBTC":
            lost_usdt = float(lost) / 1000 * cfg.BTCUSDT_PRICE
            _str = f"[{c}]{lost}{name} ({format(lost_usdt, '.2f')}$)[/{c}] locked=[cyan]{cfg.locked_balance}%[/cyan] "
        else:
            _str = f"[{c}]{lost}{name}[/{c}] locked=[cyan]{cfg.locked_balance}%[/cyan] "

        if free > 0:
            _str = f"{_str}free=[cyan]{free}{name}[/cyan] "

        log(_str, "bold", end="", fn=cfg.balance_fn)
        if count > 1:
            output = config.env[cfg.TYPE].stats.find_one(cfg.CURRENT_DATE)
            if output:
                log(f"| pos=[blue]{count}[/blue] | perf=[blue]{output['value']}[/blue]", "bold", fn=cfg.balance_fn)
            else:
                log(f"| pos=[blue]{count}[/blue]", "bold", fn=cfg.balance_fn)
        else:
            log()

        if not is_message:
            return

        if (
            cfg.discord_message
            and cfg.discord_message != ".\n"
            or (cfg.TYPE == "btc" and cfg.discord_message_full and cfg.discord_message_full != ".\n")
        ):
            if cfg.TYPE == "usdt":
                flag = False
                for symbol in config.WATCHLIST:
                    if not flag:
                        flag = True
                        msg = f"`{msg}\n```"

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
                        log(f" * {symbol}={asset_price} {per_str_c}", end="", is_write=False)

                    msg = f"{msg}\n{symbol}={asset_price} {per_str}"
                if flag:
                    msg = f"{msg}\n```"

            try:
                if cfg.discord_sent_msg:
                    await cfg.discord_sent_msg.edit(content=msg)
                else:
                    cfg.discord_sent_msg = await self.channel.send(msg)
            except Exception as e:
                print_tb(e)
                with suppress(Exception):
                    await cfg.discord_sent_msg.delete()

                cfg.discord_message = ".\n"
                cfg.discord_sent_msg = None

    ########
    # SPOT #
    ########
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
            _balances_list = await helper.exchange.spot.fetch_balance()
        except Exception as e:
            raise e

        cfg.BTCUSDT_PRICE = float(await self.spot_fetch_ticker("BTC/USDT"))
        for balance in _balances_list["info"]["balances"]:
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
                        usdt_amount = quantity * float(price) * cfg.BTCUSDT_PRICE
                        if usdt_amount > 1.0:
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

        if sum_btc > 0.00002:
            own_usdt = sum_btc * cfg.BTCUSDT_PRICE
            log(
                f" * btc=%.8f [blue]==[/blue] [cyan]%.2f$[/cyan] | bnb=[cyan]%.2f$[/cyan] | "
                f"[blue]{_date(_type='hour')}[/blue]" % (sum_btc, own_usdt, cfg.BNB_BALANCE)
            )

        if cfg.BNB_BALANCE < 1.0:
            try:
                await self.buy_bnb()
            except Exception as e:
                print_tb(e)

        pos_count: int = 0
        sum_busd = float(format(sum_busd, ".2f"))
        sum_usdt = float(format(sum_usdt, ".2f"))
        if helper.is_start > 0:
            if not helper.is_start and sum_usdt > 0.01:
                console_ruler(character="-=")

            if len(config.asset_list) == 0:
                #: cleans timestamp.yaml
                config.timestamp[f"{cfg.TYPE}_timestamp"] = dict(base=config.env[cfg.TYPE].status["timestamp"])
                _console_clear()
                if cfg.TYPE == "usdt":
                    log(f":beer:  [green]usdt=[green]{sum_usdt}", "bold")
            elif cfg.TYPE == "usdt":
                log(
                    f" * usdt={sum_usdt} | busd={sum_busd} | bnb=[cyan]{format(cfg.BNB_BALANCE, '.2f')}$[/cyan] | [blue]{_date(_type='hour')}[/blue]"
                )

            config.sum_usdt = sum_usdt
            if sum_usdt > 1.0:
                pos_count = config.env[cfg.TYPE]._status.find_one("count")["value"]
                if pos_count == 0 and config.env[cfg.TYPE].status["balance"] != sum_usdt:
                    config.env[cfg.TYPE].status["balance"] = sum_usdt

            if cfg.TYPE == "btc":
                if len(config.asset_list) == 0:
                    _console_clear()
                    log(
                        ":beer:  [bold green]spot=[/bold green]%.8f BTC [blue]==[/blue] %.2f USDT" % (sum_btc, own_usdt)
                    )

                config.env[cfg.TYPE].status["balance"] = sum_btc

        if cfg.TYPE == "usdt":
            _sum = sum_usdt
        else:
            _sum = sum_btc

        lost: float = 0.0
        cfg.locked_balance = 0.0
        cfg.discord_message = ".\n"
        cfg.discord_message_full = ".\n"
        open(cfg.balance_fn, "w").close()
        for asset in config.asset_list:
            if cfg.BALANCES:
                bal = cfg.BALANCES[asset]["total"]
                if bal > 0:
                    output = await self.spot_limit(asset, bal, _sum, is_limit)

                    lost += float(output)
                else:
                    log(f"{asset} balance is zero")
            else:
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

        locked_per = f"locked={format(cfg.locked_balance, '.2f')}%"
        if cfg.TYPE == "usdt":
            if sum_busd > 0:
                msg = (
                    f"{_msg}`{format(lost, '.2f')}$` | usdt=`{round(sum_usdt)}` | busd=`{sum_busd}` | free=`{free}` | "
                    f"total=`{round(abs(lost) + sum_usdt)}$`\n`{locked_per}` | `{_date(_type='hour')}` "
                    f"(**{pos_count}** pos)"
                )
            else:
                msg = (
                    f"{_msg}`{format(lost, '.2f')}$` | usdt=`{round(sum_usdt)}` | free=`{free}` | "
                    f"total=`{round(abs(lost) + sum_usdt)}$`\n`{locked_per}` | `{_date(_type='hour')}` "
                    f"(**{pos_count}** pos)"
                )

            cfg.SUM_BTC = 0
            cfg.SUM_USDT = format(sum_usdt, ".2f")
        else:
            msg = _msg
            if float(free) > 0:
                msg = f"{msg} free=`{free}` |"

            msg = (
                f"{msg} btc=`{format(sum_btc, '.5f')}` == `{format(own_usdt, '.2f')}$`\n`{locked_per}` | "
                f"`{_date(_type='hour')}` | pos=**{pos_count}**"
            )
            cfg.SUM_BTC = format(sum_btc, ".8f")
            cfg.SUM_USDT = format(own_usdt, ".2f")

        output = config.env[cfg.TYPE].stats.find_one(cfg.CURRENT_DATE)
        if output:
            msg = f"{msg} | perf=**{output['value']}**"

        if cfg.TYPE == "btc":
            is_message = True
            if "is_discord" in config.cfg["root"][cfg.TYPE] and config.cfg["root"][cfg.TYPE]["is_discord"] == "off":
                is_message = False

            await self._discord_send(msg, format(lost * 1000, ".5f"), pos_count, " mBTC", 0, is_message=is_message)
        else:
            await self._discord_send(msg, format(lost, ".2f"), pos_count, "$", float(free))

        config.env[cfg.TYPE]._status.add_single_key("count", count)
        self.update_timestamp_status()
        return own_usdt, sum_usdt, only_usdt, only_btc

    async def buy_bnb(self):
        log("warning: BUYING MINIMUM AMOUNT OF BNB", is_write=False)
        if cfg.TYPE == "btc":
            if float(config.env["btc"].status["free"]) < 0.0002:
                return

            output = await helper.exchange.spot.fetch_ticker("BNBBTC")
            qty = float(format(0.00015 / output["last"], ".3f"))
            order = await helper.exchange.spot.create_market_buy_order("BNBBTC", qty)
        else:
            if config.env["usdt"].status["free"] < 15:
                return

            output = await helper.exchange.spot.fetch_ticker("BNBUSDT")
            qty = float(format(11.0 / output["last"], ".3f"))
            order = await helper.exchange.spot.create_market_buy_order("BNBUSDT", qty)

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

    async def spot_order(self, quantity, symbol, side, is_return=False):
        try:
            log(f"==> market_buy_order_quantity={quantity}", "bold")
            return await helper.exchange.spot.create_market_buy_order(symbol, quantity)
        except Exception as e:
            _e = str(e)
            if "Account has insufficient balance" in _e:
                log("E: Account has insufficient balance for requested action")
                if is_return:
                    return

                quantity = quantity / 5  # re-try with the half size position
                log(f"==> re-opening {side} order, half-quantity={quantity}")
                return await self.spot_order(quantity, symbol, side, is_return=True)
            elif "Precision is over the maximum defined for this asset" in _e or "Filter failure: LOT_SIZE" in _e:
                log(f"E: {e} quantity={quantity}")
                decimal = decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                if float(_quantity) > 0:
                    return await self.spot_order(_quantity, symbol, side)
                else:
                    log("E: quantity is zero, nothing to do")
            elif "Filter failure: MIN_NOTIONAL" in _e and quantity >= 1:
                quantity += 0.1
                #: Fixes if its overrounded, ex: 1.2000000000000002
                quantity = float("{:.1f}".format(quantity))
                log(f"==> re-opening {side} order, quantity={quantity}")
                return await self.spot_order(quantity, symbol, side)
            else:
                print_tb(e)
                raise e

    async def spot_fetch_ticker(self, asset) -> float:
        if "USDT" != asset[-4:] and "BUSD" == asset[-4:]:
            asset = asset.replace("BUSD", "") + "/BUSD"
        elif "USDT" != asset[-4:] and "BTC" != asset[-3:]:
            asset = f"{asset}/BTC"

        price = await helper.exchange.spot.fetch_ticker(asset)
        return price["last"]

    async def new_limit_order(self, asset, limit_price, market="BTC"):
        """Create new limit order with the added quantity."""
        symbol = f"{asset}/{market}"
        open_orders = await helper.exchange.spot.fetch_open_orders(symbol)
        for order in open_orders:
            with suppress(Exception):
                # The order may already closed if there was a rapid change
                await helper.exchange.spot.cancel_order(order["id"], symbol)

        try:
            balance = await self.fetch_balance(asset)
            response = await helper.exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
            log("==> new_limit_order=", end="")
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
                log(f"E: Failed to create order with {symbol} [cyan]{type(e).__name__}[/cyan] {e}")

    async def fetch_balance(self, code) -> float:
        balance = await helper.exchange.spot.fetch_balance()
        return balance[code]["total"]

    ############
    # USDTPERP #
    ############
    async def _load_markets(self) -> None:
        await helper.exchange.future.load_markets()

    async def transfer_in(self, amount) -> None:
        """Transfer usdt from spot to usdtperp."""
        await helper.exchange.future.transfer_in(code="USDT", amount=amount)

    async def transfer_out(self, amount) -> None:
        """Transfer USDT from USDTDPERP to SPOT.

        __ https://github.com/ccxt/ccxt/issues/10169#issuecomment-937605731
        """
        await helper.exchange.future.transfer_out(code="USDT", amount=amount)

    async def is_future_position_open(self, symbol) -> bool:
        futures = await helper.exchange.future.fetch_balance()
        for future in futures["info"]["positions"]:
            if future["symbol"].replace("/", "") == symbol.replace("/", "") and float(future["positionAmt"]) != 0:
                return True

        return False

    async def set_leverage(self, symbol, leverage=1) -> None:
        """Set leverage for futures."""
        try:
            market = helper.exchange.future.market(symbol)
            response = await helper.exchange.future.fapiPrivate_post_leverage(
                {"symbol": market["id"], "leverage": leverage}
            )
            log(response, "bold cyan")
            response = await helper.exchange.future.fapiPrivate_post_margintype(
                {"symbol": market["id"], "marginType": "ISOLATED"}
            )
            log(response, "bold cyan")
        except Exception as e:
            if "No need to change margin type" not in str(e):
                print_tb(e)

    async def futures_fetch_ticker(self, asset) -> float:
        price = await helper.exchange.future.fetch_ticker(asset)
        return float(price["last"])
