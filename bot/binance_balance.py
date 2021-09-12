#!/usr/bin/env python3

import asyncio
import os
import time
from contextlib import suppress
from typing import Dict

from bot import helper
from bot.bot_helper_async import TP, BotHelperAsync
from bot.config import config
from bot.user_setup import check_binance_obj
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils.tools import _colorize_traceback, _exit, _time, delete_last_line, log, percent_change

client, _ = check_binance_obj()
bot_async = BotHelperAsync()


def future_stats(usdt_bal, unix_timestamp_ms):
    log(f" * Futures={format(usdt_bal, '.2f')}", end="")
    log("___________________________________________", "blue", end="")
    log(f"{_time().replace('2021-','')} {unix_timestamp_ms}", "yellow")


async def _create_market_order(symbol: str, amount, side):
    """Create market order for futures."""
    if side == "BUY":
        order = await helper.exchange.future.create_market_buy_order(symbol, amount)
    elif side == "SELL":
        order = await helper.exchange.future.create_market_sell_order(symbol, amount)

    with suppress(Exception):
        log(f"market_order={order['info']}")


async def _create_limit_order(symbol, position_amt, limit_price, side):
    """Create limit order.

    :param side: is the original side of the strategy
    """
    if side == "BUY":
        order = await helper.exchange.future.create_limit_sell_order(symbol, position_amt, limit_price)
    elif side == "SELL":
        order = await helper.exchange.future.create_limit_buy_order(symbol, position_amt, limit_price)

    log(f"limit_order={order['info']}")


async def cancel_check_orders(symbol, limit_price, side, entry_price, position_amt) -> None:
    """Cancel orders based on the -N% loss.

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
            log("")
            if delta_change > 0.05:
                order_p = float(order["info"]["price"])
                if (side == "BUY" and (limit_price < order_p or order_p < entry_price)) or (
                    side == "SELL" and (limit_price > order_p or order_p > entry_price)
                ):  # noqa
                    await helper.exchange.future.cancel_order(order["id"], symbol)
                    cancel_flag = True

        if cancel_flag:
            await _create_limit_order(symbol, position_amt, limit_price, side)
    else:
        if await bot_async.is_future_position_open(symbol):
            await _create_limit_order(symbol, position_amt, limit_price, side)


async def process_future_positions(future_positions, usdt_bal, unix_timestamp_ms):
    print_flag = False
    usdt_bal += config.TRBINANCE_USDT  # USDT on trbinance is added
    count = 0
    for position in future_positions:
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
            _decimal_count = bot_async.get_precision(price_dict)
            price = price_dict["last"]
            if position_amt < 0.0:
                log("==> ", "red", end="")
                side = "SELL"
                change = entry_price - price
                limit_price = (
                    f"{float(entry_price) * TP.get_profit_amount('short', isolated_wallet):.{_decimal_count}f}"
                )
            else:
                log("==> ", "green", end="")
                side = "BUY"
                change = price - entry_price
                limit_price = f"{float(entry_price) * TP.get_profit_amount('long', isolated_wallet):.{_decimal_count}f}"

            _str = "{0: <5}".format(symbol.replace("/USDT", ""))
            log(f"{_str} e={format(entry_price, '.4')} l={format(float(limit_price), '.4f')}", end="")
            unrealized_profit = float(format(float(position["info"]["unrealizedProfit"]), ".2f"))
            log(f" {unrealized_profit}", "red" if unrealized_profit < 0.0 else "green", end="")
            asset_percent_change = percent_change(entry_price, change, is_arrow_print=False, end="")
            per = (100.0 * initial_margin) / usdt_bal
            _per = format(per, ".2f")
            log("| ", end="")
            log(f"{format(isolated_wallet, '.2f')}", "magenta", is_bold=True, end="")
            log(f"({_per}%) ", "magenta", is_bold=True, end="")
            if asset_percent_change <= config.PERCENT_CHANGE_TO_ADD_USDT + 0.01:
                new_amount = abs(position_amt) * config.USDT_MULTIPLY_RATIO
                new_amount_margin = isolated_wallet * config.USDT_MULTIPLY_RATIO
                per = (100.0 * (isolated_wallet + new_amount_margin)) / usdt_bal
                _per = format(per, ".2f")
                if float(_per) <= config.LOCKED_PERCENT_LIMIT_USDT:
                    await _create_market_order(symbol, new_amount, side)
                else:
                    if float(_per) < 100:
                        log(f"\n    Warning: Total locked amount is more than {_per}%", end="")

            await cancel_check_orders(symbol, limit_price, side, entry_price, position_amt)

    config.status["futures"]["pos_count"] = count
    return print_flag


async def process_main(channel=None):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    if channel:
        bot_async.channel = channel

    config.reload()
    bot_async.futures_balance = await helper.exchange.future.fetch_balance()
    unix_timestamp_ms = helper.exchange.get_future_timestamp()
    try:
        *_, usdt_bal = await bot_async.spot_balance()
        if usdt_bal > 0.0 and not helper.is_start:
            log("")

        config.status["futures"]["free"] = float(bot_async.futures_balance["free"]["USDT"]) + usdt_bal
        usdt_bal += float(bot_async.futures_balance["total"]["USDT"])
        usdt_bal += float(bot_async.futures_balance["total"]["BUSD"])
        # TODO: pozisyonlarin o anki son fiyati olmali?
        future_positions = await helper.exchange.future.fetch_positions()
        is_printed = await process_future_positions(future_positions, usdt_bal, unix_timestamp_ms)
        if not is_printed and not helper.is_start:
            delete_last_line()

        if not is_printed or helper.is_start:
            future_stats(usdt_bal, unix_timestamp_ms)
            helper.is_start = False
    except KeyError:
        _exit("E: KeyError")
        os._exit(0)  # kill the process
    except Exception as e:
        _colorize_traceback(e)
        await bot_async._sleep(30)


async def _main():  # noqa
    while True:
        try:
            await process_main()
            await _sleep(22)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            _colorize_traceback(e)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_main())
    except KeyboardInterrupt:
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(bot_async.close())
    except Exception as e:
        _colorize_traceback(e)
        time.sleep(120)
        loop.run_until_complete(_main())
    finally:
        log("Program finished.", "green")
