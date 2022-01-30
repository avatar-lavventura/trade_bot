#!/usr/bin/env python3

import asyncio
from contextlib import suppress
from typing import Dict

from ccxt.base.errors import RequestTimeout  # noqa
from filelock import FileLock

from bot import helper
from bot.bot_helper_async import TP
from bot.bot_helper_async_usdt import BotHelperUsdtAsync
from bot.config import config
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import _exit, _time, delete_multiple_lines, percent_change, print_tb
from ebloc_broker.broker.errors import QuietExit

RUN_FUTURES = False
bot_async = BotHelperUsdtAsync()


def future_stats(usdt_bal, unix_timestamp_ms):
    with FileLock(config.status.fp_lock, timeout=1):
        locked = usdt_bal - config.status["root"]["free_usdt"]
        if not isinstance(config.status["log"]["futures"]["max_locked"], int):
            config.status["log"]["futures"]["max_locked"] = 0

        if locked > config.status["log"]["futures"]["max_locked"]:
            config.status["log"]["futures"]["max_locked"] = locked

        locked_per = (100.0 * locked) / usdt_bal
        config.status["futures"]["total"] = usdt_bal
        config.status["futures"]["locked"] = locked
        config.status["futures"]["locked_per"] = locked_per

    is_write = True
    if float(locked) == 0.0:
        is_write = False
        log(f" * balance={format(usdt_bal, '.2f')}", end="", is_write=is_write)
        log("_____________________", "bold blue", end="", is_write=is_write)
    else:
        log(f" * balance={format(usdt_bal, '.2f')} | ", end="")
        log(f"locked={format(locked, '.2f')}({format(locked_per, '.2f')}%)", "bold", end="")

    log("_______________", "bold blue", end="", is_write=is_write)
    log(f"{_time().replace('2021-','')} {unix_timestamp_ms}", "yellow", is_write=is_write)


def futures_bal(info, asset) -> float:
    return float(bot_async.futures_balance[info][asset])


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
            raise QuietExit(f"warning: Not enough free USDT, amount={new_amount} margin={new_amount_margin}")
    else:
        if _per < 100:
            log(f"warning: Total locked amount is {_per}%", end="")


async def process_future_positions(positions, usdt_bal, unix_timestamp_ms, channel=None):
    print_flag = False
    with suppress(Exception):
        usdt_bal += config.trbinance_usdt

    total_lost = 0
    count = 0
    for position in positions:
        #: Indicates total locked amount without applying any gain or loss
        isolated_wallet = abs(float(position["info"]["isolatedWallet"]))
        #: Indicates amount of collateral that is locked up
        initial_margin = abs(float(position["info"]["initialMargin"]))
        if isolated_wallet > 0.0:
            count += 1
            if not print_flag:
                future_stats(usdt_bal, unix_timestamp_ms)
                print_flag = True

            symbol = position["symbol"]
            entry_price = float(position["entryPrice"])
            position_amt = float(position["info"]["positionAmt"])
            price_dict = await helper.exchange.future.fetch_ticker(symbol)
            price = price_dict["last"]
            precision = helper.exchange.future_markets[symbol]["precision"]["price"]
            if position_amt < 0:
                log("==> ", "red", end="")
                side = "SELL"
                change = entry_price - price
                limit_price = f"{float(entry_price) * TP.get_profit_amount('short', isolated_wallet):.{precision}f}"
            else:
                log("==> ", "green", end="")
                side = "BUY"
                change = price - entry_price
                limit_price = f"{float(entry_price) * TP.get_profit_amount('long', isolated_wallet):.{precision}f}"

            asset = "{0: <5}".format(symbol.replace("/USDT", ""))
            log(
                f"{asset} e={format(entry_price, '.4')} l={format(float(limit_price), '.4f')} | p={price}",
                "bold",
                end="",
            )
            if float(entry_price) < 0 or float(limit_price) < 0:
                update_spot_timestamp(unix_timestamp_ms)
                return

            unrealized_profit = float(format(float(position["info"]["unrealizedProfit"]), ".2f"))
            log(f" {unrealized_profit}", "red" if unrealized_profit < 0 else "green", end="")
            total_lost -= unrealized_profit
            asset_percent_change = percent_change(entry_price, change, is_arrow_print=False, end="")
            per = format((100.0 * initial_margin) / usdt_bal, ".2f")
            log("| ", end="")
            log(f"{format(isolated_wallet, '.2f')}", "bold magenta", end="")
            log(f"({per}%) ", "bold magenta", end="")
            if isolated_wallet > config.isolated_wallet_limit:
                log(f"Warning: calc_locked={per}% ", end="")

            if isolated_wallet > config.discord_msg_above_usdt:
                await channel.send(
                    f"{asset} isolated_wallet={int(isolated_wallet)}, "
                    f"unrealized_profit={unrealized_profit}({format(asset_percent_change, '.2f')}%)",
                    delete_after=20,  # new message will come in 20 seconds
                )

            if (
                isolated_wallet < config.isolated_wallet_limit
                and asset_percent_change <= config.USDTPERP_PERCENT_CHANGE_TO_ADD
            ):
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal)
            elif isolated_wallet > config.isolated_wallet_limit and asset_percent_change <= -7.0 and float(per) < 30.0:
                # when isolated_wallet is greater than isolated_wallet_limit (~100$)
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal, mul=1, per=50.0)

            await cancel_check_orders(symbol, limit_price, side, entry_price, position_amt)

    if total_lost > 0.0125:
        log(f"total_lost={format(total_lost, '.2f')}$", "bold red")

    with FileLock(config.status.fp_lock, timeout=1):
        if config.status["futures"]["pos_count"] != count:
            config.status["futures"]["pos_count"] = count

        if not isinstance(config.status["log"]["futures"]["max_position_count"], int):
            config.status["log"]["futures"]["max_position_count"] = 0

        if count > config.status["log"]["futures"]["max_position_count"]:
            config.status["log"]["futures"]["max_position_count"] = count

    return print_flag


def update_spot_timestamp(unix_timestamp_ms: int):
    if not isinstance(config.run_balance["root"]["timestamp"], int):
        config.run_balance["root"]["timestamp"] = 0

    if unix_timestamp_ms > config.run_balance["root"]["timestamp"]:
        config.run_balance["root"]["timestamp"] = unix_timestamp_ms

    if unix_timestamp_ms > config.timestamp["spot_timestamp"]["base"]:
        config.timestamp["spot_timestamp"]["base"] = unix_timestamp_ms


def _percent(amount, ratio):
    return float(format(amount * ratio / 100, ".2f"))


async def process_main(obj):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    bot_async.channel = obj.channel
    bot_async.channel_alerts = obj.channel_alerts
    config.reload()
    try:
        if not RUN_FUTURES:
            unix_timestamp_ms = helper.exchange.get_spot_timestamp()

        update_spot_timestamp(unix_timestamp_ms)  # first update spot.timestamp
        *_, usdt_bal, free_usdt = await bot_async.spot_balance()
        if RUN_FUTURES:
            bot_async.futures_balance = await helper.exchange.future.fetch_balance()
            unix_timestamp_ms = helper.exchange.get_future_timestamp()

        if usdt_bal > 0.125 and not helper.is_start:
            log()

        if RUN_FUTURES:
            with FileLock(config.status.fp_lock, timeout=1):
                config.status["root"]["free_usdt"] = futures_bal("free", "USDT") + usdt_bal

            usdt_bal += futures_bal("total", "USDT") + futures_bal("total", "BUSD")
        else:
            with FileLock(config.status.fp_lock, timeout=1):
                config.status["root"]["_balance"] = usdt_bal
                config.status["root"]["free_usdt"] = free_usdt

        for idx in range(1, 6):
            config.status["risk"][f"{idx}_per"] = _percent(config.status["root"]["_balance"], idx)

        if RUN_FUTURES:
            positions = await helper.exchange.future.fetch_positions()
            is_printed = await process_future_positions(positions, usdt_bal, unix_timestamp_ms, bot_async.channel)
            if not is_printed and not helper.is_start and config.status["spot"]["pos_count"] == 0:
                delete_multiple_lines(2)

            if not is_printed or helper.is_start:
                future_stats(usdt_bal, unix_timestamp_ms)
                helper.is_start = False
        elif helper.is_start and config.status["spot"]["pos_count"] == 0:
            delete_multiple_lines(1)

        # for alert in config.ALERTS:
        #     if _alert:
        #         asset_price = await bot_async.spot_fetch_ticker(_alert["pair"])
        #         if float(asset_price) > _alert["price"]:
        #             await bot_async.channel_alerts.send(f"{_alert['pair']}={asset_price}", delete_after=19)

    except RequestTimeout:
        _exit("Timestamp for this request is outside of the recieve_window=5000")
    except KeyError as e:
        print_tb(e)
        _exit("KeyError")
    except Exception as e:
        if "quantity is zero" in str(e):
            log(f"warning: {e}, nothing to worry about", "bold")
        else:
            print_tb(e)
            await _sleep(30)


async def main():
    await helper.exchange.set_markets()
    while True:
        try:
            await process_main(bot_async)
            await _sleep(22)
        except KeyboardInterrupt:
            break
        except Exception as e:
            if "Timestamp for this request is outside of the recvWindow" in str(e):
                log(f"E: {e}")
            else:
                print_tb(e)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())
    except QuietExit as e:
        if e:
            log(str(e))
    except Exception as e:
        print_tb(e)
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())

        # time.sleep(120)
        # loop.run_until_complete(main())  # infinite loop
