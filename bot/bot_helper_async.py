#!/usr/bin/env python3

from contextlib import suppress

from bot import helper
from bot.config import config
from ebloc_broker.broker._utils.tools import _colorize_traceback, decimal_count, log, percent_change, round_float


class TP_calculate(Exception):  # noqa
    pass


class TakeProfit:
    def __init__(self):
        self.TAKE_PROFIT_LONG = []
        self.TAKE_PROFIT_SHORT = []
        self.take_profit_percent: float = config.TP
        # index:0 => 0.5% Profit
        self.TAKE_PROFIT_LONG.append(1.000 + self.take_profit_percent)
        self.TAKE_PROFIT_SHORT.append(1.000 - self.take_profit_percent)
        # index:1 => 0.5 * 2 (1%) Profit
        self.TAKE_PROFIT_LONG.append(1.000 + self.take_profit_percent * 2)
        self.TAKE_PROFIT_SHORT.append(1.000 - self.take_profit_percent * 2)

    def get_profit_amount(self, side, amount=0.0) -> float:
        amount = abs(float(amount))
        index = 0
        if side == "long":
            quantity = config.INITIAL_USDT_QTY_LONG
        else:  # side == "short":
            quantity = config.INITIAL_USDT_QTY_SHORT

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
        pass

    async def close(self):
        """Close async function.

        https://stackoverflow.com/a/54528397/2402577
        """
        await helper.exchange._close()

    ###########
    # FUTURES #
    ###########
    async def _load_markets(self):
        await helper.exchange.future.load_markets()

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
            log(response, "cyan")

            response = await helper.exchange.future.fapiPrivate_post_margintype(
                {"symbol": market["id"], "marginType": "ISOLATED"}
            )
            log(response, "cyan")
        except Exception as e:
            if "No need to change margin type." not in str(e):
                _colorize_traceback(e)

    async def futures_fetch_ticker(self, asset) -> float:
        price = await helper.exchange.future.fetch_ticker(asset)
        return float(price["last"])

    ########
    # SPOT #
    ########
    async def spot_balance(self, is_limit=True):
        """Calculate USDT balance in spot."""
        usdt_amount = 0.0
        sum_btc = 0.0
        count = 0
        balances = await helper.exchange.spot.fetch_balance()
        for balance in balances["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                quantity = float(balance["free"]) + float(balance["locked"])
                if asset == "BTC":
                    sum_btc += quantity
                else:
                    if asset not in ["USDT", "BNB"]:
                        # TODO: check float(balance["free"]) USDT value if > 1.0 USDT
                        count += 1
                        price = await self.spot_fetch_ticker(asset)
                        sum_btc += quantity * float(price)
                    elif asset == "USDT":
                        usdt_amount = quantity

        current_btc_price_USD = await self.spot_fetch_ticker("BTC/USDT")
        own_usd = sum_btc * float(current_btc_price_USD)
        if sum_btc > 0.0:
            log(" * Spot=%.8f BTC == %.2f USDT" % (sum_btc, own_usd))

        for balance in balances["info"]["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                with suppress(Exception):
                    btc_quantity = float(balance["free"]) + float(balance["locked"])
                    if asset not in ["BTC", "BNB", "USDT"]:
                        await self.spot_limit(asset, btc_quantity, sum_btc, is_limit)

        config.status["spot"]["pos_count"] = count
        return own_usd, float(usdt_amount)

    async def spot_order(self, quantity, symbol, side):
        try:
            log(f"==> order_quantity={quantity}")
            return await helper.exchange.spot.create_market_buy_order(symbol, quantity)
        except Exception as e:
            if "Precision is over the maximum defined for this asset" in str(e) or "Filter failure: LOT_SIZE" in str(e):
                log(f"E: {e} quantity={quantity}")
                decimal = decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening {side} order, quantity={_quantity}")
                if float(_quantity) > 0.0:
                    return await self.spot_order(_quantity, symbol, side)
                else:
                    log("E: quantity is zero, nothing to do.")
            elif "Filter failure: MIN_NOTIONAL" == getattr(e, "message", repr(e)) and quantity >= 1:
                quantity += 0.1
                quantity = float("{:.1f}".format(quantity))  # sometimes overround 1.2000000000000002
                log(f"==> re-opening {side} order, quantity={quantity}")
                return await self.spot_order(quantity, symbol, side)
            else:
                _colorize_traceback(e)
                raise e

    async def spot_fetch_ticker(self, asset) -> float:
        if "USDT" not in asset and "BTC" not in asset:
            asset = asset + "/BTC"

        price = await helper.exchange.spot.fetch_ticker(asset)
        return float(price["last"])

    async def new_limit_order(self, asset, limit_price):
        """Create new limit order with the added quantity."""
        symbol = f"{asset}/BTC"
        open_orders = await helper.exchange.spot.fetch_open_orders(symbol)
        for order in open_orders:
            try:
                await helper.exchange.spot.cancel_order(order["id"], symbol)
            except Exception as e:
                _colorize_traceback(e)

        try:
            balance = await self.fetch_balance(asset)
            respone = await helper.exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
            log("==> New limit-order is placed:")
            log(respone, "cyan")
        except Exception as e:
            log("Failed to create order with", helper.exchange.spot.id, type(e).__name__, str(e), "red")

    async def fetch_balance(self, code) -> float:
        balance = await helper.exchange.spot.fetch_balance()
        return balance[code]["total"]

    async def spot_limit(self, asset, asset_balance, sum_btc, is_limit=True):
        """Spot limit.

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

        https://stackoverflow.com/a/18016874/2402577
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
        # trades_usdt = await helper.exchange.spot.fetch_my_trades(asset + "/USDT", since=_since)
        # all_trades = trades + trades_usdt  # merge USDT transactions
        all_trades = trades
        ordering = {}
        for idx, trade in enumerate(all_trades):
            try:
                # In case orders occur in the same timestamp
                ordering[trade["timestamp"]].append(idx)
            except:
                ordering[trade["timestamp"]] = [idx]

        # Sort transactions based on their timestamp
        timestamp_list = sorted(ordering, reverse=True)
        for index in enumerate(timestamp_list):
            for inner_index in ordering[index[1]]:
                trade = all_trades[inner_index]
                decimal = decimal_count(trade["price"])
                if decimal > decimal:
                    decimal = decimal

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
            log(f"Warning: {asset} sum={_sum} qty={quantity} asset_balance={asset_balance}")
            entry_price = 0.0005738
            # for index in enumerate(timestamp_list):
            #     trade = all_trades[ordering[index[1]]]
            #     print(f"{trade['timestamp']} {trade['info']['qty']}")
        else:
            entry_price = float(f"{entry_price:.{decimal}f}")

        limit_price = f"{entry_price * TP.get_profit_amount('long'):.{decimal}f}"
        log(f"==> {asset} quantity={asset_balance} | ", end="")
        log(f"entry_price={entry_price} | ", end="")
        if is_limit and asset not in config.IGNORE_LIST_SPOT:
            log(f"limit_price={limit_price} ", end="")

        asset_price = await self.spot_fetch_ticker(asset)
        per = (100.0 * asset_balance * asset_price) / sum_btc
        _per = format(per, ".2f")
        log(f"{_per}% ", "blue", end="")
        asset_percent_change = percent_change(
            initial=entry_price, change=asset_price - entry_price, is_arrow_print=False
        )

        if not is_limit or asset in config.IGNORE_LIST_SPOT:
            return

        if asset_percent_change <= config.PERCENT_CHANGE_TO_ADD_SPOT + 0.01 and _per < 50.0:
            new_order_size = asset_balance * config.SPOT_MULTIPLY_RATIO
            log(f"new_order_size={new_order_size} | ", "blue", end="")
            per = (100.0 * (asset_balance + new_order_size) * asset_price) / sum_btc
            _per = format(per, ".2f")
            log(f"==> {_per} of the total asset value")
            if float(_per) <= config.LOCKED_PERCENT_LIMIT_SPOT:
                order = await self.spot_order(new_order_size, _symbol, "BUY")
                log(order["info"])
                await self.new_limit_order(asset, limit_price)
            else:
                new_per = (100.0 * asset_balance * asset_price) / sum_btc
                per_to_buy = config.LOCKED_PERCENT_LIMIT_SPOT - abs(new_per)
                btc_amount_to_buy = per_to_buy * sum_btc / 100.0
                _new_order_size = btc_amount_to_buy / asset_price
                _new_order_size = f"{_new_order_size:.{decimal}f}"
                order = await self.spot_order(_new_order_size, _symbol, "BUY")
                log(order["info"])
                await self.new_limit_order(asset, limit_price)

        open_orders = await helper.exchange.spot.fetch_open_orders(f"{asset}/BTC")
        if not open_orders:
            await self.new_limit_order(asset, limit_price)
        else:
            for order in open_orders:
                if order["info"]["side"] == "SELL":
                    if float(limit_price) < float(order["price"]):
                        await self.new_limit_order(asset, limit_price)
