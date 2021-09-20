#!/usr/bin/env python3

import asyncio
import math
from contextlib import suppress

import yfinance as yf

from bot import helper
from bot.bot_helper_async import BotHelperAsync
from bot.config import config
from bot.trade_async import BotHelper
from bot.user_setup import check_binance_obj
from ebloc_broker.broker._utils._async import _sleep
from ebloc_broker.broker._utils.tools import _colorize_traceback, _time, log

client, _ = check_binance_obj()
bot = BotHelper(client)
bot_async = BotHelperAsync()


def get_silver(silver_gr: float) -> float:
    """Return silver price."""
    msft = yf.Ticker("SI=F")
    info = msft.info
    silver_oz_price = info["regularMarketPrice"]
    oz_to_gram = 31.103477
    return (silver_oz_price / oz_to_gram) * silver_gr


async def goal():
    goal_sum = 0.0
    with suppress(TypeError):
        goal_sum += config.goal["goal"]["USDT"]

    with suppress(TypeError):
        goal_sum += config.goal["goal"]["BTC"] * await bot_async.spot_fetch_ticker("BTC/USDT")

    with suppress(TypeError):
        goal_sum += config.goal["goal"]["TRY"] / await bot_async.spot_fetch_ticker("USDT/TRY")

    if math.ceil(goal_sum) > 0.0:
        log(" | ", end="")
        log(f"goal={math.ceil(goal_sum)} USDT", "bold green")


async def fetch_balance() -> float:
    total_lost = 0.0
    total_balance = 0.0
    print_flag = False
    try:
        own_usd, future_balance = await bot_async.spot_balance(is_limit=False)
        total_balance = float(own_usd)
        bot_async.futures_balance = await helper.exchange.future.fetch_balance()
        future_balance += float(bot_async.futures_balance["total"]["USDT"])
        total_balance += future_balance
        future_balance = format(future_balance, ".2f")
        log(f" * {_time()} | Futures={future_balance}", end="")
        await goal()
        future_positions = await helper.exchange.future.fetch_positions()
        for position in future_positions:
            initial_margin = abs(float(position["info"]["isolatedWallet"]))
            if initial_margin > 0.0:
                if print_flag:
                    log("")
                else:
                    print_flag = True

                symbol = position["symbol"]
                entry_price = float(position["entryPrice"])
                symbol_temp = symbol.replace("/USDT", "")
                log(f"==> {symbol_temp} entry={entry_price}", end="")
                unrealized_profit = float(format(float(position["info"]["unrealizedProfit"]), ".2f"))
                if unrealized_profit < 0.0:
                    log(f" {unrealized_profit}", "red", end="")
                    total_lost -= unrealized_profit
                else:
                    log(f" {unrealized_profit}", "green", end="")
                    total_lost -= unrealized_profit

                usdt_balance = float(bot_async.futures_balance["total"]["USDT"])
                per = (100.0 * initial_margin) / usdt_balance
                log(f" {format(per, '.2f')}% ", "blue", end="")
                log(f"{format(initial_margin, '.2f')} ", "blue", end="")

        log(f"total_lost={int(total_lost)}", "bold red")
        return total_balance
    except Exception as e:
        _colorize_traceback(e)
    finally:
        await helper.exchange.future.close()
        await helper.exchange.spot.close()


async def main():
    """Start fetching balance."""
    while True:
        await fetch_balance()
        log("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", "cyan")
        await _sleep(30)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(bot_async.close())
    except Exception as e:
        _colorize_traceback(e)
    finally:
        log("Program finished.", "bold green")
