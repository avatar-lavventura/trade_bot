#!/usr/bin/env python3

import asyncio
import time
from contextlib import suppress
from typing import Dict

from filelock import FileLock

from bot import helper
from bot.bot_helper_async import TP  # , BotHelperAsync
from bot.bot_helper_async_usdt import BotHelperUsdtAsync
from bot.config import config
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils._log import log
from ebloc_broker.broker._utils.tools import QuietExit, _exit, _time, delete_last_line, percent_change, print_tb

bot_async = BotHelperUsdtAsync()


def future_stats(usdt_bal, unix_timestamp_ms):
    with FileLock(config.status.fp_lock, timeout=1):
        locked = usdt_bal - config.status["futures"]["free"]
        try:
            if locked > config.status["log"]["futures"]["max_locked"]:
                config.status["log"]["futures"]["max_locked"] = locked
        except TypeError:
            config.status["log"]["futures"]["max_locked"] = 0

        locked_per = (100.0 * locked) / usdt_bal
        config.status["futures"]["total"] = usdt_bal
        config.status["futures"]["locked"] = locked
        config.status["futures"]["locked_per"] = locked_per

    if float(locked) == 0.0:
        log(f" * balance={format(usdt_bal, '.2f')}", end="", is_log=False)
        log("______________________", "bold blue", end="", is_log=False)
        log("_______________", "bold blue", end="", is_log=False)
        log(f"{_time().replace('2021-','')} {unix_timestamp_ms}", "yellow", is_log=False)
    else:
        log(f" * balance={format(usdt_bal, '.2f')}", end="")
        log(
            f" | locked={format(locked, '.2f')}({format(locked_per, '.2f')}%)", "bold", end="",
        )
        log("_______________", "bold blue", end="")
        log(f"{_time().replace('2021-','')} {unix_timestamp_ms}", "yellow")


def futures_bal(info, asset) -> float:
    return float(bot_async.futures_balance[info][asset])


async def create_market_order(symbol: str, amount, side) -> None:
    """Create market order for futures."""
    if side == "BUY":
        order = await helper.exchange.future.create_market_buy_order(symbol, amount)
    elif side == "SELL":
        order = await helper.exchange.future.create_market_sell_order(symbol, amount)

    with suppress(Exception):
        log(f"[bold]market_order=[/bold][white]{order['info']}")


async def create_limit_order(symbol, position_amt, limit_price, side):
    """Create limit order.

    :param side: is the original side of the strategy
    """
    if side == "BUY":
        order = await helper.exchange.future.create_limit_sell_order(symbol, position_amt, limit_price)
    elif side == "SELL":
        order = await helper.exchange.future.create_limit_buy_order(symbol, position_amt, limit_price)

    log(f"[bold]limit_order=[/bold][white]{order['info']}")


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
            log()
            if delta_change > 0.05:
                order_p = float(order["info"]["price"])
                is_cancel_buy_side = side == "BUY" and (limit_price < order_p or order_p < entry_price)
                if is_cancel_buy_side or (side == "SELL" and (limit_price > order_p or order_p > entry_price)):
                    await helper.exchange.future.cancel_order(order["id"], symbol)
                    cancel_flag = True

        if cancel_flag:
            await create_limit_order(symbol, position_amt, limit_price, side)
    else:
        if await bot_async.is_future_position_open(symbol):
            await create_limit_order(symbol, position_amt, limit_price, side)


async def new_order(symbol, side, position_amt, isolated_wallet, usdt_bal, mul=None, percent=None):
    # Add more money only if the position is less than given amount(ex: 50$)
    # TODO: if unrealized > 5% close the position, improve
    if not percent:
        percent = config.locked_per_limit_usdtperp

    if not mul:
        mul = config.USDTPERP_MULTIPLY_RATIO

    new_amount = abs(position_amt) * mul
    new_amount_margin = isolated_wallet * mul
    per = (100.0 * (isolated_wallet + new_amount_margin)) / usdt_bal
    _per = float(format(per, ".2f"))
    if _per <= percent:
        if config.status["futures"]["free"] > new_amount:
            await create_market_order(symbol, new_amount, side)
        else:
            raise QuietExit("Warning: Not enough free USDT")
    else:
        if _per < 100:
            log(f"Warning: Total locked amount is {_per}%", end="")


async def process_future_positions(positions, usdt_bal, unix_timestamp_ms):
    print_flag = False
    usdt_bal += config.trbinance_usdt
    count = 0
    total_lost = 0
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
            if position_amt < 0.0:
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

            log(f"{asset} e={format(entry_price, '.4')} l={format(float(limit_price), '.4f')}", "bold", end="")
            if float(entry_price) < 0 or float(limit_price) < 0:
                update_spot_timestamp(unix_timestamp_ms)
                return

            unrealized_profit = float(format(float(position["info"]["unrealizedProfit"]), ".2f"))
            log(f" {unrealized_profit}", "red" if unrealized_profit < 0.0 else "green", end="")
            total_lost -= unrealized_profit
            asset_percent_change = percent_change(entry_price, change, is_arrow_print=False, end="")
            per = (100.0 * initial_margin) / usdt_bal
            _per = format(per, ".2f")
            log("| ", end="")
            log(f"{format(isolated_wallet, '.2f')}", "bold magenta", end="")
            log(f"({_per}%) ", "bold magenta", end="")
            if isolated_wallet > config.isolated_wallet_limit:
                log(f"Warning: Calculated locked amount is {_per}% ", end="")

            if (
                isolated_wallet < config.isolated_wallet_limit
                and asset_percent_change <= config.USDTPERP_PERCENT_CHANGE_TO_ADD
            ):
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal)
            elif isolated_wallet > config.isolated_wallet_limit and asset_percent_change <= -7.0 and float(_per) < 30.0:
                # when isolated_wallet is greater than isolated_wallet_limit(~100$)
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal, 1.0, percent=50.0)

            await cancel_check_orders(symbol, limit_price, side, entry_price, position_amt)

    if total_lost > 0.00:
        log(f"total_lost={format(total_lost, '.2f')}$", "bold red")

    with FileLock(config.status.fp_lock, timeout=1):
        if config.status["futures"]["pos_count"] != count:
            config.status["futures"]["pos_count"] = count

        try:
            if count > config.status["log"]["futures"]["max_position_count"]:
                config.status["log"]["futures"]["max_position_count"] = count
        except TypeError:
            config.status["log"]["futures"]["max_position_count"] = 0

    return print_flag


def update_spot_timestamp(unix_timestamp_ms: int):
    try:
        if unix_timestamp_ms > config.timestamp["spot_timestamp"]["base"]:
            config.timestamp["spot_timestamp"]["base"] = unix_timestamp_ms
    except TypeError:
        config.timestamp["spot_timestamp"]["base"] = 0


async def process_main(channel=None):
    """Process binance check operations.

    __ https://github.com/ccxt/ccxt/issues/9678#issuecomment-889993445
    """
    # await channel.send("alper")
    config.reload()
    try:
        *_, usdt_bal = await bot_async.spot_balance()
        bot_async.futures_balance = await helper.exchange.future.fetch_balance()
        unix_timestamp_ms = helper.exchange.get_future_timestamp()
        if config.status["spot"]["pos_count"] == 0:
            update_spot_timestamp(unix_timestamp_ms)

        if usdt_bal > 0.0 and not helper.is_start:
            log("")

        with FileLock(config.status.fp_lock, timeout=1):
            config.status["futures"]["free"] = futures_bal("free", "USDT") + usdt_bal

        usdt_bal += futures_bal("total", "USDT") + futures_bal("total", "BUSD")
        # TODO: pozisyonlarin o anki son fiyati olmali?
        positions = await helper.exchange.future.fetch_positions()
        is_printed = await process_future_positions(positions, usdt_bal, unix_timestamp_ms)
        if not is_printed and not helper.is_start and config.status["spot"]["pos_count"] == 0:
            delete_last_line(2)

        if not is_printed or helper.is_start:
            future_stats(usdt_bal, unix_timestamp_ms)
            helper.is_start = False
    except KeyError:
        print_tb()
        _exit("E: KeyError")
    except Exception as e:
        print_tb(e)
        await _sleep(30)


async def main():
    await helper.exchange.set_markets()
    while True:
        try:
            await process_main()
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
            log(e)
    except Exception as e:
        print_tb(e)
        time.sleep(120)
        loop.run_until_complete(main())
    finally:
        log("FIN")
