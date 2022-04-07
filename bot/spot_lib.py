#!/usr/bin/env python3

from contextlib import suppress
from typing import Dict

from broker._utils._log import log
from broker.errors import QuietExit

from bot import cfg, helper
from bot.bot_helper_async_usdt import BotHelperSpotAsync
from bot.config import config

bot_async = BotHelperSpotAsync()


def print_order(order, _type) -> None:
    with suppress(Exception):
        del order["info"]["closePosition"]
        del order["info"]["timeInForce"]
        del order["info"]["positionSide"]
        del order["info"]["priceProtect"]
        del order["info"]["reduceOnly"]
        del order["info"]["workingType"]

    log(f"[bold]{_type}=[/bold][white]{order['info']}")


async def create_market_order(symbol: str, amount, side) -> None:
    """Create market order for futures."""
    if side == "BUY":
        order = await helper.exchange.future.create_market_buy_order(symbol, amount)
    elif side == "SELL":
        order = await helper.exchange.future.create_market_sell_order(symbol, amount)

    print_order(order, "market_order")


async def new_order(symbol, side, position_amt, isolated_wallet, usdt_bal, mul=None, per=None) -> None:
    if not per:
        per = config.locked_per_limit_usdtperp

    if not mul:
        mul = config.USDTPERP_MULTIPLY_RATIO

    new_amount = abs(position_amt) * mul
    #: locked money in the position
    new_amount_margin = isolated_wallet * mul
    per = (100.0 * (isolated_wallet + new_amount_margin)) / usdt_bal
    _per = float(format(per, ".2f"))
    if _per <= per:
        if config.status["root"]["free_usdt"] > abs(new_amount_margin):
            await create_market_order(symbol, new_amount, side)
        else:
            raise QuietExit(f"warning: not enough free USDT, amount={new_amount} margin={new_amount_margin}")
    else:
        if _per < 100:
            log(f"warning: Total locked amount is {_per}%", end="")


def update_spot_timestamp(unix_timestamp_ms: int):
    if not isinstance(config.env[cfg.TYPE].status["timestamp"], int):
        config.env[cfg.TYPE].status["timestamp"] = 0

    if unix_timestamp_ms > config.env[cfg.TYPE].status["timestamp"]:
        config.env[cfg.TYPE].status["timestamp"] = unix_timestamp_ms


async def create_limit_order(symbol, position_amt, limit_price, side) -> None:
    """Create limit order.

    :param symbol: of the limit order
    :param side: is the original side of the strategy
    """
    if side == "BUY":
        order = await helper.exchange.future.create_limit_sell_order(symbol, position_amt, limit_price)
    elif side == "SELL":
        order = await helper.exchange.future.create_limit_buy_order(symbol, position_amt, limit_price)

    print_order(order, "limit_order")


async def cancel_check_orders(symbol, limit_price, side, entry_price, position_amt) -> None:
    """Cancel orders based on the -n% loss.

    Delta change track is applied. Rounding may cause some error. ex: 1.2497 ~= 1.25
    """
    cancel_count = {}  # type: Dict[str, int]
    position_amt = abs(position_amt)
    limit_price = float(limit_price)
    open_orders = await helper.exchange.future.fetch_open_orders(symbol)
    if len(open_orders) > 0:
        cancel_flag = False
        for order in open_orders:
            with suppress(Exception):
                if cancel_count[order["symbol"]]:
                    # in case multipe same orders are open should be closed
                    await helper.exchange.future.cancel_order(order["id"], symbol)

            cancel_count[order["symbol"]] = True
            order_p = float(order["info"]["price"])
            delta_change = 100.0 * abs(limit_price - order_p) / order_p
            log()
            if delta_change > 0.05:
                order_p = float(order["info"]["price"])
                is_cancel_buy_side = side == "BUY" and (limit_price < order_p or order_p < entry_price)
                if is_cancel_buy_side or (side == "SELL" and (limit_price > order_p or order_p > entry_price)):
                    await helper.exchange.future.cancel_order(order["id"], symbol)
                    cancel_flag = True

        if cancel_flag:
            await create_limit_order(symbol, position_amt, limit_price, side)
    elif await bot_async.is_future_position_open(symbol):
        await create_limit_order(symbol, position_amt, limit_price, side)
