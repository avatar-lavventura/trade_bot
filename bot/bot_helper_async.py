#!/usr/bin/env python3

from broker._utils._log import _console_clear, console_ruler, log
from broker._utils.tools import _date, decimal_count, percent_change, print_tb, round_float
from contextlib import suppress
from filelock import FileLock
from typing import List, Tuple

from bot import cfg, helper
from bot.config import config


class TP_calculate(Exception):
    pass


class TakeProfit:
    def __init__(self):
        self.take_profit: float = config.take_profit
        self.TAKE_PROFIT: List[float] = []
        # index:0 => 0.5% profit
        self.TAKE_PROFIT.append(1.000 + self.take_profit)
        # index:1 => ex: 0.5 * 2 (1%) profit
        multiply_ratio = 1
        self.TAKE_PROFIT.append(1.000 + self.take_profit * multiply_ratio)

    def get_profit_amount(self, amount=0) -> float:
        amount = abs(float(amount))
        index = 0
        # if side == "long":
        #     quantity = config._initial_usdt_qty
        # else:  # side == "short":
        #     quantity = config._initial_usdt_qty_short

        # if amount > (quantity + quantity / 2):
        #     # if the initial margin is more than first opened position amount
        #     index = 1
        return self.TAKE_PROFIT[index]

    def get_long_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * self.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price <= entry_price:
            raise TP_calculate(f"limit_price={price}, decimal={decimal} calculated wrong")

        return price

    def get_short_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * TP.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price >= entry_price:
            raise TP_calculate(f"limit_price={price}, decimal={decimal} calculated wrong")

        return price


TP = TakeProfit()


class BotHelperAsync:
    def __init__(self):
        self.balances = []

    async def close(self):
        """Close async function.

        https://stackoverflow.com/a/54528397/2402577
        """
        await helper.exchange.close()

    ############
    # USDTPERP #
    ############
    async def _load_markets(self):
        await helper.exchange.future.load_markets()

    async def transfer_in(self, amount):
        """Transfer usdt from spot to usdtperp."""
        await helper.exchange.future.transfer_in(code="USDT", amount=amount)

    async def transfer_out(self, amount):
        """Transfer USDT from USDTDPERP to SPOT.

        __ https://github.com/ccxt/ccxt/issues/10169#issuecomment-937605731
        """
        await helper.exchange.future.transfer_out(code="USDT", amount=amount)

    async def is_future_position_open(self, symbol_original) -> bool:
        futures = await helper.exchange.future.fetch_balance()
        for future in futures["info"]["positions"]:
            if float(future["positionAmt"]) != 0.0:
                if future["symbol"].replace("/", "") == symbol_original.replace("/", ""):
                    return True

        return False

    async def set_leverage(self, symbol, leverage=1):
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
            if "No need to change margin type." not in str(e):
                print_tb(e)

    async def futures_fetch_ticker(self, asset) -> float:
        price = await helper.exchange.future.fetch_ticker(asset)
        return float(price["last"])

    def update_timestamp_status(self):
        del_list = []
        key = f"{cfg.TYPE.lower()}_timestamp"
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp != "base" and asset_timestamp not in config.asset_list:
                ts = int(config.timestamp[key][asset_timestamp])
                if len(str(ts)) == 13:
                    if ts <= config.run_balance["root"]["timestamp"] * 1000:
                        del_list.append(asset_timestamp)
                elif ts <= config.run_balance["root"]["timestamp"]:
                    del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

    async def _discord_send(self, msg, _lost, count, name):
        cfg.locked_balance = float(format(cfg.locked_balance, ".2f"))
        if cfg.locked_balance > 0:
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- ", "gray", end="", fn=cfg.balance_fn)
            log(
                f"[red]{_lost}{name}[/red] locked={cfg.locked_balance}% [blue]{count}[/blue] pos",
                "bold",
                fn=cfg.balance_fn,
            )

        if cfg.discord_message != ".\n":
            try:
                if cfg.discord_sent_message:
                    await cfg.discord_sent_message.edit(content=msg)
                else:
                    cfg.discord_sent_message = await self.channel.send(msg)
            except:
                cfg.discord_sent_message = ".\n"

    ########
    # SPOT #
    ########
    async def spot_balance(self, is_limit=True) -> Tuple[float, float, float]:
        """Calculate USDT balance in spot."""
        own_usd: float = 0
        sum_usdt: float = 0
        sum_btc: float = 0
        only_usdt: float = 0
        count = 0
        config.asset_list = []
        try:
            self.balances = await helper.exchange.spot.fetch_balance()
        except Exception as e:
            raise e

        btcusdt_price = float(await self.spot_fetch_ticker("BTC/USDT"))
        for balance in self.balances["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                quantity = float(balance["free"]) + float(balance["locked"])
                if asset == "BTC":
                    sum_btc += quantity
                else:

                    if asset not in cfg.STABLE_COINS:
                        # price = await self.spot_fetch_ticker(asset)
                        price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")
                        if cfg.TYPE == "usdt":
                            usdt_to_added = quantity * float(price)
                            if usdt_to_added > 10:  # TODO: check float(balance["free"]) USDT value if > 1.0 USDT
                                # below 10$ would not count as open position
                                config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                                config.asset_list.append(asset)
                                if asset not in config.SPOT_IGNORE_LIST:
                                    count += 1
                        elif cfg.TYPE == "btc":
                            sum_btc += quantity * float(price)
                            usdt_to_added = quantity * float(price) * btcusdt_price
                            if usdt_to_added > 4:
                                config.btc_quantity[asset] = float(balance["free"]) + float(balance["locked"])
                                config.asset_list.append(asset)
                                if asset not in config.SPOT_IGNORE_LIST:
                                    count += 1

                        sum_usdt += usdt_to_added
                    elif asset == cfg.TYPE.upper():
                        only_usdt = quantity
                        sum_usdt += quantity

        if sum_btc > 0.00002:
            own_usd = sum_btc * btcusdt_price
            log(
                f" * btc=%.8f [blue]==[/blue] [cyan]%.2f$[/cyan] | [magenta]{int(btcusdt_price)}[/magenta]"
                f" [blue]{_date(_type='hour')}[/blue]" % (sum_btc, own_usd)
            )

        sum_usdt = float(format(sum_usdt, ".2f"))
        if helper.is_start or config.total_position_count() > 0:
            if not helper.is_start and sum_usdt > 0.01:
                console_ruler(character="-=")

            if len(config.asset_list) == 0:
                #: cleans timestamp.yaml
                config.timestamp[f"{cfg.TYPE.lower()}_timestamp"] = dict(base=config.run_balance["root"]["timestamp"])
                _console_clear()
                if cfg.TYPE.lower() == "usdt":
                    log(f":beer:  [green]usdt=[green]{sum_usdt}", "bold")
            else:
                if cfg.TYPE.lower() == "usdt":
                    log(f" * usdt={sum_usdt} | [blue]{_date(_type='hour')}[/blue]")

            config.sum_usdt = sum_usdt
            if sum_usdt > 1.0:
                if cfg.TYPE.lower() == "usdt":
                    pos_count = config.status_usdt["count"]
                elif cfg.TYPE.lower() == "btc":
                    pos_count = config.status_btc["count"]

                if pos_count == 0 and config.status["root"][cfg.TYPE]["balance"] != sum_usdt:
                    with FileLock(config.status.fp_lock, timeout=5):
                        config.status["root"][cfg.TYPE]["balance"] = sum_usdt

            if cfg.TYPE.lower() == "btc":
                if len(config.asset_list) == 0:
                    _console_clear()
                    log(":beer:  [bold green]spot=[/bold green]%.8f BTC [blue]==[/blue] %.2f USDT" % (sum_btc, own_usd))

                config.status["root"][cfg.TYPE]["balance"] = sum_btc

        if cfg.TYPE.lower() == "usdt":
            _sum = sum_usdt
        else:
            _sum = sum_btc

        lost = 0.0
        cfg.discord_message = ".\n"
        cfg.discord_message_full = ".\n"
        cfg.locked_balance = 0.0
        open(cfg.balance_fn, "w").close()
        for asset in config.asset_list:
            lost += await self.spot_limit(asset, config.btc_quantity[asset], _sum, is_limit)
            # await self.spot_limit(asset, btc_quantity, sum_btc, is_limit)

        if abs(lost) < 5:
            msg = f"{cfg.discord_message}lost=`{format(lost, '.2f')}$` | usdt=`{round(sum_usdt)}`"
        else:
            msg = f"{cfg.discord_message_full}lost=`{format(lost, '.2f')}$` | usdt=`{round(sum_usdt)}`"

        msg = f"{msg}\n`{_date(_type='hour')}`"

        if cfg.TYPE.lower() == "usdt":
            if lost < -0.1:
                await self._discord_send(msg, format(lost, ".2f"), pos_count, "$")
            else:
                try:
                    if cfg.discord_sent_message:
                        await cfg.discord_sent_message.delete()
                        cfg.discord_sent_message = None
                except:
                    cfg.discord_sent_message = None

            with FileLock(config.status_usdt.fp_lock, timeout=5):
                config.status_usdt["count"] = count
        elif cfg.TYPE.lower() == "btc":
            await self._discord_send(msg, format(lost * 1000, ".5f"), pos_count, " mBTC")
            with FileLock(config.status_btc.fp_lock, timeout=5):
                config.status_btc["count"] = count

        self.update_timestamp_status()
        return own_usd, sum_usdt, only_usdt

    async def spot_order(self, quantity, symbol, side):
        try:
            log(f"==> market_buy_order_quantity={quantity}", "bold")
            return await helper.exchange.spot.create_market_buy_order(symbol, quantity)
        except Exception as e:
            if "Account has insufficient balance" in str(e):
                log("E: Account has insufficient balance for requested action")
                return
            elif "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(
                e
            ):
                log(f"E: {e} quantity={quantity}")
                decimal = decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return await self.spot_order(_quantity, symbol, side)
                else:
                    log("E: quantity is zero, nothing to do")
            elif "Filter failure: MIN_NOTIONAL" in str(e) and quantity >= 1:
                quantity += 0.1
                #: Fixes if its overrounded, ex: 1.2000000000000002
                quantity = float("{:.1f}".format(quantity))
                log(f"==> re-opening {side} order, quantity={quantity}")
                return await self.spot_order(quantity, symbol, side)
            else:
                print_tb(e)
                raise e

    async def spot_fetch_ticker(self, asset) -> float:
        if "USDT" not in asset and "BTC" not in asset:
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
            log("==> new_limit_order:")
            if "info" in response:
                response = response["info"]

            with suppress(Exception):
                del response["status"]
                del response["clientOrderId"]
                del response["timeInForce"]
                del response["cummulativeQuoteQty"]
                del response["orderListId"]

            log(response, "bold cyan")
        except Exception as e:
            if type(e).__name__ != "InvalidOrder":
                log(f"E: Failed to create order with {type(e).__name__} {e}")

    async def fetch_balance(self, code) -> float:
        balance = await helper.exchange.spot.fetch_balance()
        return balance[code]["total"]

    async def spot_limit(self, asset, asset_balance, sum_bal, is_limit=True):
        """Order spot limit.

        * Python sort list based on key sorted list:
        __ https://stackoverflow.com/a/18016874/2402577
        """
        decimal = 0
        _sum = 0.0
        quantity = 0.0
        try:
            _since = config.get_spot_timestamp(asset)
            if not _since:
                _since = config.SPOT_TIMESTAMP
        except:
            _since = config.SPOT_TIMESTAMP

        trades = await helper.exchange.spot.fetch_my_trades(asset + "/BTC", since=_since)
        ordering = {}
        for idx, trade in enumerate(trades):
            try:
                # in case orders occur in the same timestamp
                ordering[trade["timestamp"]].append(idx)
            except:
                ordering[trade["timestamp"]] = [idx]

        # Sort transactions based on their timestamp
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

        asset_percent_change = percent_change(
            initial=entry_price, change=asset_price - entry_price, is_arrow_print=False
        )
        if asset_percent_change <= config.SPOT_PERCENT_CHANGE_TO_ADD and float(per) < 50.0:
            new_order_size = asset_balance * config.SPOT_MULTIPLY_RATIO
            log(f"==> new_order_size={new_order_size} | {per} of the total asset value", end="")
            if float(per) <= config.SPOT_locked_percent_limit:
                order = await self.spot_order(new_order_size, f"{asset}/BTC", "BUY")
                log(order["info"], "bold")
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
        if not open_orders:
            await self.new_limit_order(asset, limit_price)
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL" and float(limit_price) < float(order["price"]):
                    await self.new_limit_order(asset, limit_price)
