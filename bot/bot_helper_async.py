#!/usr/bin/env python3


from contextlib import suppress
from typing import Tuple

from broker._utils._log import _console_clear, console_ruler, log
from broker._utils.tools import _date, decimal_count, print_tb
from filelock import FileLock

from bot import cfg, helper
from bot.config import config
from bot.take_profit import TakeProfit

TP = TakeProfit()


class BotHelperAsync:
    def __init__(self):
        self.balances = []

    async def close(self):
        """Close async function.

        __ https://stackoverflow.com/a/54528397/2402577
        """
        await helper.exchange.close()

    def update_timestamp_status(self) -> None:
        del_list = []
        key = f"{cfg.TYPE}_timestamp"
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp != "base" and asset_timestamp not in config.asset_list:
                ts = int(config.timestamp[key][asset_timestamp])
                if len(str(ts)) == 13:
                    if ts <= config.env[cfg.TYPE].status["timestamp"] * 1000:
                        del_list.append(asset_timestamp)
                elif ts <= config.env[cfg.TYPE].status["timestamp"]:
                    del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

        if cfg.TYPE == "usdt" and config.cfg["root"]["busd"]["status"] == "on":
            # check to delete LUNA input
            key = "busd_timestamp"
            for asset_timestamp in config.timestamp[key]:
                if asset_timestamp not in config.asset_list:
                    ts = int(config.timestamp[key][asset_timestamp])
                    if len(str(ts)) == 13:
                        if ts <= config.env[cfg.TYPE].status["timestamp"] * 1000:
                            del_list.append(asset_timestamp)
                    elif ts <= config.env[cfg.TYPE].status["timestamp"]:
                        del_list.append(asset_timestamp)

            for asset in del_list:
                del config.timestamp[key][asset]

    async def _discord_send(self, msg, lost, count, name, free=0):
        cfg.locked_balance = float(format(cfg.locked_balance, ".2f"))
        if cfg.locked_balance > 99.9:
            cfg.locked_balance = 100

        c = "red" if float(lost) < 0 < cfg.locked_balance else "green"
        log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- ", "gray", end="", fn=cfg.balance_fn)
        _str = f"[{c}]{lost}{name}[/{c}] locked=[cyan]{cfg.locked_balance}%[/cyan] "
        if free > 0:
            _str = f"{_str}free=[cyan]{free}{name}[/cyan] "

        log(_str, "bold", end="", fn=cfg.balance_fn)
        if count > 1:
            log(f"[blue]{count}[/blue] pos", "bold", fn=cfg.balance_fn)
        else:
            log()

        if (
            cfg.discord_message
            and cfg.discord_message != ".\n"
            or (cfg.TYPE == "btc" and cfg.discord_message_full and cfg.discord_message_full != ".\n")
        ):
            if cfg.TYPE == "usdt":
                for symbol in config.WATCHLIST:
                    _asset_price = await self.spot_fetch_ticker(symbol)
                    msg = f"{msg}\n - {symbol}={_asset_price}"
                    # log(f"[cyan]**[/cyan] {symbol}={_asset_price}", "bold")

            try:
                if cfg.discord_sent_msg:
                    await cfg.discord_sent_msg.edit(content=msg)
                else:
                    cfg.discord_sent_msg = await self.channel.send(msg)
            except:
                with suppress(Exception):
                    await cfg.discord_sent_msg.delete()

                cfg.discord_message = ".\n"
                cfg.discord_sent_msg = None

    ########
    # SPOT #
    ########
    async def spot_balance(self, is_limit=True) -> Tuple[float, float, float, float]:
        """Calculate USDT balance in spot."""
        own_usd: float = 0
        sum_usdt: float = 0
        sum_busd: float = 0
        sum_btc: float = 0
        only_usdt: float = 0
        only_btc: float = 0
        count: int = 0
        config.asset_list = []
        try:
            self.balances = await helper.exchange.spot.fetch_balance()
        except Exception as e:
            raise e

        cfg.BTCUSDT_PRICE = float(await self.spot_fetch_ticker("BTC/USDT"))
        for balance in self.balances["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0 or float(balance["locked"]) != 0:
                quantity = float(balance["free"]) + float(balance["locked"])
                if asset == "BTC":
                    only_btc = quantity
                    sum_btc += quantity
                elif asset not in cfg.STABLE_COINS:
                    price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")
                    if cfg.TYPE == "usdt":
                        usdt_to_added = quantity * float(price)
                        if usdt_to_added > 1.0:  # below 1.0$ would not count as open position
                            config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1
                    elif cfg.TYPE == "btc":
                        sum_btc += quantity * float(price)
                        usdt_to_added = quantity * float(price) * cfg.BTCUSDT_PRICE
                        if usdt_to_added > 1.0:
                            config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1

                    sum_usdt += usdt_to_added
                elif asset.lower() == cfg.TYPE:
                    only_usdt = quantity
                    sum_usdt += quantity
                elif asset.lower() == "busd":
                    sum_busd += quantity

        if sum_btc > 0.00002:
            own_usd = sum_btc * cfg.BTCUSDT_PRICE
            log(
                f" * btc=%.8f [blue]==[/blue] [cyan]%.2f$[/cyan] | [magenta]{int(cfg.BTCUSDT_PRICE)}[/magenta]"
                f" [blue]{_date(_type='hour')}[/blue]" % (sum_btc, own_usd)
            )

        pos_count = 0
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
                log(f" * usdt={sum_usdt} | busd={sum_busd} | [blue]{_date(_type='hour')}[/blue]")

            config.sum_usdt = sum_usdt
            if sum_usdt > 1.0:
                if cfg.TYPE == "usdt":
                    pos_count = config.status_usdt["count"]
                elif cfg.TYPE == "btc":
                    pos_count = config.status_btc["count"]

                if pos_count == 0 and config.env[cfg.TYPE].status["balance"] != sum_usdt:
                    config.env[cfg.TYPE].status["balance"] = sum_usdt

            if cfg.TYPE == "btc":
                if len(config.asset_list) == 0:
                    _console_clear()
                    log(":beer:  [bold green]spot=[/bold green]%.8f BTC [blue]==[/blue] %.2f USDT" % (sum_btc, own_usd))

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
            msg = (
                f"{_msg}`{format(lost, '.2f')}$` | usdt=`{round(sum_usdt)}` | busd=`{sum_busd}` | free=`{free}` | "
                f"total=`{round(abs(lost) + sum_usdt)}$`\n`{locked_per}` | `{_date(_type='hour')}`"
            )
        else:
            msg = _msg
            if float(free) > 0:
                msg = f"{msg} free=`{free}` |"

            msg = f"{msg} total=`{format(own_usd, '.2f')}$` (btc=`{format(sum_btc, '.4f')}`)\n`{locked_per}` | `{_date(_type='hour')}`"

        if cfg.TYPE == "usdt":
            if lost < -0.1:
                await self._discord_send(msg, format(lost, ".2f"), pos_count, "$", float(free))
            else:
                try:
                    if cfg.discord_sent_msg:
                        await cfg.discord_sent_msg.delete()
                        cfg.discord_sent_msg = None
                except:
                    cfg.discord_sent_msg = None

            with FileLock(config.status_usdt.fp_lock, timeout=5):
                config.status_usdt["count"] = count
        else:
            await self._discord_send(msg, format(lost * 1000, ".5f"), pos_count, " mBTC")
            with FileLock(config.status_btc.fp_lock, timeout=5):
                config.status_btc["count"] = count

        self.update_timestamp_status()
        return own_usd, sum_usdt, only_usdt, only_btc

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
        if "BUSD" in asset:
            asset = asset.replace("BUSD", "") + "/BUSD"
        elif "USDT" not in asset and "BTC" not in asset:
            asset = f"{asset}/BTC"

        price = await helper.exchange.spot.fetch_ticker(asset)
        return float(price["last"])

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
