#!/usr/bin/env python3

from contextlib import suppress
from typing import Tuple

from filelock import FileLock

from bot import cfg, helper
from bot.config import config
from ebloc_broker.broker._utils._log import _console_clear, console_ruler, log
from ebloc_broker.broker._utils.tools import _time, decimal_count, percent_change, print_tb, round_float


class TP_calculate(Exception):
    pass


class TakeProfit:
    def __init__(self):
        self.TAKE_PROFIT_LONG = []
        self.TAKE_PROFIT_SHORT = []
        self.take_profit_percent: float = config.take_profit
        # index:0 => 0.5% Profit
        self.TAKE_PROFIT_LONG.append(1.000 + self.take_profit_percent)
        self.TAKE_PROFIT_SHORT.append(1.000 - self.take_profit_percent)
        # index:1 => ex: 0.5 * 2 (1%) Profit
        multiply_ratio = 1
        self.TAKE_PROFIT_LONG.append(1.000 + self.take_profit_percent * multiply_ratio)
        self.TAKE_PROFIT_SHORT.append(1.000 - self.take_profit_percent * multiply_ratio)

    def get_profit_amount(self, side, amount=0.0) -> float:
        amount = abs(float(amount))
        index = 0
        if side == "long":
            quantity = config._initial_usdt_qty_long
        else:  # side == "short":
            quantity = config._initial_usdt_qty_short

        if amount > (quantity + quantity / 2):
            # if the initial margin is more than first opened position amount
            index = 1

        if side == "long":
            return self.TAKE_PROFIT_LONG[index]
        else:  # side == "short":
            return self.TAKE_PROFIT_SHORT[index]

    def get_long_tp(self, entry_price, isolated_wallet, decimal):
        price = f"{float(entry_price) * self.get_profit_amount('long', isolated_wallet):.{decimal}f}"
        price = float(price)
        if price <= entry_price:
            raise TP_calculate(f"E: limit_price={price}, decimal={decimal} calculated wrong.")

        return price

    def get_short_tp(self, entry_price, isolated_wallet, decimal):
        price = f"{float(entry_price) * TP.get_profit_amount('short', isolated_wallet):.{decimal}f}"
        price = float(price)
        if price >= entry_price:
            raise TP_calculate(f"E: limit_price={price}, decimal={decimal} calculated wrong.")

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
        """Transfer USDT from usdtperp to spot.

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
                if len(str(config.timestamp[key][asset_timestamp])) == 13:
                    if int(config.timestamp[key][asset_timestamp]) <= config.run_balance["root"]["timestamp"] * 1000:
                        del_list.append(asset_timestamp)
                else:
                    if int(config.timestamp[key][asset_timestamp]) <= config.run_balance["root"]["timestamp"]:
                        del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

    ########
    # SPOT #
    ########
    async def spot_balance(self, is_limit=True, balance_type="usdt") -> Tuple[float, float, float]:
        """Calculate USDT balance in spot."""
        own_usd = 0.0
        sum_usdt = 0.0
        sum_btc = 0.0
        count = 0
        only_usdt = 0.0
        config.asset_list = []
        try:
            self.balances = await helper.exchange.spot.fetch_balance()
        except Exception as e:
            raise e

        current_btc_price = float(await self.spot_fetch_ticker("BTC/USDT"))
        for balance in self.balances["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                quantity = float(balance["free"]) + float(balance["locked"])
                if asset == "BTC":
                    sum_btc += quantity
                else:
                    if asset not in ["USDT", "BNB", "ETH", "PAX", "PAXG"]:
                        # price = await self.spot_fetch_ticker(asset)
                        # sum_btc += quantity * float(price)
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
                            usdt_to_added = quantity * float(price) * current_btc_price
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
            own_usd = sum_btc * current_btc_price
            log(" * Spot=%.8f BTC == %.2f USDT" % (sum_btc, own_usd))

        sum_usdt = float(format(sum_usdt, ".2f"))
        if helper.is_start or config.total_position_count() > 0:
            if not helper.is_start and sum_usdt > 0.01:
                console_ruler(character="-=")

            if len(config.asset_list) == 0:
                #: cleans timestamp.yaml
                config.timestamp[f"{cfg.TYPE.lower()}_timestamp"] = dict(base=config.run_balance["root"]["timestamp"])
                _console_clear()
                log(f":beer: [bold green]usdt=[/bold green]{sum_usdt}")
            else:
                log(f" * usdt={sum_usdt}")

            config.sum_usdt = sum_usdt
            if sum_usdt > 1.0:
                if cfg.TYPE.lower() == "usdt":
                    pos_count = config.status_usdt["count"]
                elif cfg.TYPE.lower() == "btc":
                    pos_count = config.status_btc["count"]

                if pos_count == 0 and config.status["root"][cfg.TYPE]["balance"] != sum_usdt:
                    with FileLock(config.status.fp_lock, timeout=1):
                        config.status["root"][cfg.TYPE]["balance"] = sum_usdt

            if cfg.TYPE.lower() == "btc":
                _console_clear()
                log(" * Spot=%.8f BTC == %.2f USDT" % (sum_btc, own_usd))
                if cfg.TYPE == "btc":
                    config.status["root"][cfg.TYPE]["balance"] = sum_btc

        total_lost = 0.0
        cfg.discord_message = ".\n"
        open("balance.log", "w").close()
        for asset in config.asset_list:
            total_lost += await self.spot_limit_usdt(asset, config.btc_quantity[asset], sum_usdt, is_limit)  # noqa
            # await self.spot_limit(asset, btc_quantity, sum_btc, is_limit)

        msg = f"{cfg.discord_message}total_lost=`{format(total_lost, '.2f')}$` | usdt=`{sum_usdt}$`"
        if total_lost < -0.1:
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- ", "gray", end="", filename="balance.log")
            log(f"{format(total_lost, '.2f')}$ [blue]{_time(_type='hour')}", "red", filename="balance.log")
            if cfg.discord_message != ".\n":
                cfg.discord_sent_message = await self.channel.send(msg, delete_after=19)

        if cfg.TYPE.lower() == "usdt":
            with FileLock(config.status_usdt.fp_lock, timeout=1):
                config.status_usdt["count"] = count
        elif cfg.TYPE.lower() == "btc":
            with FileLock(config.status_btc.fp_lock, timeout=1):
                config.status_btc["count"] = count

        self.update_timestamp_status()
        return own_usd, sum_usdt, only_usdt

    async def spot_order(self, quantity, symbol, side):
        try:
            log(f"==> market_buy_order_quantity={quantity}", "bold")
            output = await helper.exchange.spot.create_market_buy_order(symbol, quantity)
            return output
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
            log("==> new limit-order:")
            if "info" in response:
                log(response["info"], "bold cyan")
            else:
                log(response, "bold cyan")
        except Exception as e:
            if type(e).__name__ != "InvalidOrder":
                log(f"E: Failed to create order with {type(e).__name__} {e}")

    async def fetch_balance(self, code) -> float:
        balance = await helper.exchange.spot.fetch_balance()
        return balance[code]["total"]

    async def spot_limit(self, asset, asset_balance, sum_btc, is_limit=True):
        """Order spot limit.

        475.0
        1104.0
        1082.0
        1104.0
        1084.0
        1104.0 <== breaks
        1083.0
        1104.0
        1083.0
        1104.0
        1092.0
        1104.0
        1027.0

        __ https://stackoverflow.com/a/18016874/2402577
        """
        _symbol = f"{asset}/BTC"
        _sum = 0.0
        quantity = 0.0
        decimal = 0
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
                # botrade_cost = qty * float(trade["info"]["price"])
                trade_cost = trade["cost"]  # ignoring fees
                if trade["info"]["isBuyer"]:
                    # log(qty, "green")
                    quantity += qty
                    _sum += trade_cost
                else:
                    # log(qty, "red")
                    quantity -= qty
                    _sum -= trade_cost

                quantity = round_float(quantity, 8)
                _sum = round_float(_sum, 8)

                # try:
                #     _quantity[quantity] += 1
                #     if _quantity[quantity] > 3:
                #         is_break = True
                # except:
                #     _quantity[quantity] = 1
                # if is_break:
                #     break

        entry_price = _sum / quantity
        if _sum <= 0 or abs(quantity - asset_balance) > 0.01:
            log(f"warning: {asset} sum={_sum} qty={quantity} asset_balance={asset_balance}")
            entry_price = 0.0005738
        else:
            entry_price = float(f"{entry_price:.{decimal}f}")

        limit_price = f"{entry_price * TP.get_profit_amount('long'):.{decimal}f}"
        log(f"==> {asset} quantity={asset_balance} | entry_price={entry_price} | ", end="")
        if is_limit and asset not in config.SPOT_IGNORE_LIST:
            log(f"limit_price={limit_price} ", end="")

        try:
            asset_price = await self.spot_fetch_ticker(asset)
        except Exception as e:
            raise Exception(f"asset({asset}) is not found in ticker") from e

        per = (100.0 * asset_balance * asset_price) / sum_btc
        _per = format(per, ".2f")
        log(f"{_per}% ", "blue", end="")
        asset_percent_change = percent_change(
            initial=entry_price, change=asset_price - entry_price, is_arrow_print=False
        )

        if not is_limit or asset in config.SPOT_IGNORE_LIST:
            return

        if asset_percent_change <= config.SPOT_PERCENT_CHANGE_TO_ADD and float(_per) < 50.0:
            new_order_size = asset_balance * config.SPOT_MULTIPLY_RATIO
            per = (100.0 * (asset_balance + new_order_size) * asset_price) / sum_btc
            log(f"==> new_order_size={new_order_size} | {_per} of the total asset value", end="")
            if float(_per) <= config.SPOT_locked_percent_limit:
                order = await self.spot_order(new_order_size, _symbol, "BUY")
                log(order["info"], "bold")
                await self.new_limit_order(asset, limit_price)
            else:
                new_per = (100.0 * asset_balance * asset_price) / sum_btc
                per_to_buy = config.SPOT_locked_percent_limit - abs(new_per)
                btc_amount_to_buy = per_to_buy * sum_btc / 100.0
                _new_order_size = btc_amount_to_buy / asset_price
                _new_order_size = f"{_new_order_size:.{decimal}f}"
                order = await self.spot_order(_new_order_size, _symbol, "BUY")
                log(order["info"], "bold")
                await self.new_limit_order(asset, limit_price)

        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BTC")
        if not open_orders:
            await self.new_limit_order(asset, limit_price)
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL" and float(limit_price) < float(order["price"]):
                    await self.new_limit_order(asset, limit_price)
