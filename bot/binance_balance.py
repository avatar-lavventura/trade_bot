#!/usr/bin/env python3

import asyncio
import os
from pathlib import Path

import ccxt.async_support as ccxt
from broker._utils.tools import _colorize_traceback, _time, log
from broker.libs.math import percent_change
from dotenv import load_dotenv

import bot.helper as helper
from bot.bot_helper_async import (
    LOCKED_PERCENT_LIMIT_USDT,
    PERCENT_CHANGE_TO_ADD_USDT,
    TAKE_PROFIT_LONG,
    TAKE_PROFIT_SHORT,
    USDT_MULTIPLY_RATIO,
    BotHelperAsync,
)
from bot.trade import BotHelper
from bot.user_setup import check_binance_obj

HOME = str(Path.home())
load_dotenv(override=True)

client, _ = check_binance_obj()
bot = BotHelper(client)
load_dotenv(override=True)

SLEEP_TIME = float(os.getenv("SLEEP_TIME"))
bot_async = BotHelperAsync()


async def close():
    """doc: https://stackoverflow.com/a/54528397/2402577"""
    log("Finalazing...")
    await asyncio.sleep(1)


async def spot_balance():
    sum_btc = 0.0
    balances = await helper.exchange.spot.fetch_balance()
    for balance in balances["info"]["balances"]:
        asset = balance["asset"]
        if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
            btc_quantity = float(balance["free"]) + float(balance["locked"])
            if asset == "BTC":
                sum_btc += btc_quantity
            else:
                if asset != "USDT" and asset != "BNB":
                    price = await bot_async.spot_fetch_ticker(asset)
                    sum_btc += btc_quantity * float(price)

    current_btc_price_USD = await bot_async.spot_fetch_ticker("BTC/USDT")
    own_usd = sum_btc * float(current_btc_price_USD)
    log("")
    log(" * Spot => %.8f BTC == " % sum_btc, end="")
    log("%.8f USDT" % own_usd)
    for balance in balances["info"]["balances"]:
        asset = balance["asset"]
        if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
            try:
                btc_quantity = float(balance["free"]) + float(balance["locked"])
                if asset not in ["BTC", "BNB"]:
                    trades = await helper.exchange.spot.fetch_my_trades(asset + "/BTC")
                    await bot_async.spot_limit(asset, trades, btc_quantity, sum_btc)
            except:
                pass


async def main():
    while True:
        try:
            try:
                bot_async.futures_balance = await helper.exchange.future.fetch_balance()
            except Exception as e:
                _colorize_traceback(e)

            log(f" * {_time()} | Futures={bot_async.futures_balance['total']['USDT']}")
            future_positions = await helper.exchange.future.fetch_positions()
            for position in future_positions:
                initial_margin = abs(float(position["info"]["positionInitialMargin"]))
                if initial_margin > 0.0:
                    symbol_original = position["symbol"]
                    _symbol = position["symbol"]
                    entry_price = float(position["entryPrice"])
                    price_dict = await helper.exchange.future.fetch_ticker(_symbol)
                    _decimal_count = bot_async.get_precision(price_dict)
                    price = price_dict["last"]
                    limit_price = None
                    position_amt = float(position["info"]["positionAmt"])
                    if position_amt < 0.0:
                        _side = "SELL"
                        change = entry_price - price
                        limit_price = f"{float(entry_price) * TAKE_PROFIT_SHORT:.{_decimal_count}f}"
                    else:
                        _side = "BUY"
                        change = price - entry_price
                        limit_price = f"{float(entry_price) * TAKE_PROFIT_LONG:.{_decimal_count}f}"

                    log(
                        f"==> {_symbol.replace('/USDT', '')} entry={entry_price}, limit={limit_price}, side={_side} ",
                        end="",
                    )
                    unrealized_profit = float(format(float(position["info"]["unrealizedProfit"]), ".2f"))
                    if unrealized_profit < 0.0:
                        log(f" {unrealized_profit}", color="red", end="")
                    else:
                        log(f" {unrealized_profit}", color="green", end="")

                    asset_percent_change = percent_change(
                        initial=entry_price, change=change, is_arrow_print=False, end=""
                    )
                    usdt_balance = float(bot_async.futures_balance["total"]["USDT"])
                    per = (100.0 * initial_margin) / usdt_balance
                    _per = format(per, ".2f")
                    log(f"{_per}% ", color="blue", end="")
                    log(f"{format(initial_margin, '.2f')} ", end="", color="blue")
                    if asset_percent_change <= PERCENT_CHANGE_TO_ADD_USDT:
                        new_amount = abs(position_amt) * USDT_MULTIPLY_RATIO
                        new_amount_margin = initial_margin * USDT_MULTIPLY_RATIO
                        per = (100.0 * (initial_margin + new_amount_margin)) / usdt_balance
                        _per = format(per, ".2f")
                        if float(_per) <= LOCKED_PERCENT_LIMIT_USDT:
                            if _side == "BUY":
                                order = await helper.exchange.future.create_market_buy_order(_symbol, new_amount)
                                log(order, color="cyan")

                            elif _side == "SELL":
                                order = await helper.exchange.future.create_market_sell_order(_symbol, new_amount)
                                log(order, color="cyan")
                        else:
                            log(f"Warning: Total locked amount exceeds {_per}", end="")

                    try:
                        cancel_count = {}
                        open_orders = await helper.exchange.future.fetch_open_orders(_symbol)
                        if len(open_orders) > 0:
                            cancel_flag = False
                            for order in open_orders:
                                try:
                                    if cancel_count[order["symbol"]]:
                                        # in case multipe same orders are open
                                        await helper.exchange.future.cancel_order(order["id"], _symbol)
                                except:
                                    pass

                                cancel_count[order["symbol"]] = True
                                order_price = float(order["info"]["price"])
                                delta_change = 100.0 * abs(float(limit_price) - order_price) / order_price
                                # log(f"delta_change={delta_change}")
                                log("")
                                if delta_change > 0.05:
                                    # Rounding may cause some error. ex: 1.2497 ~= 1.25
                                    order_price = float(order["info"]["price"])
                                    if _side == "BUY":
                                        if float(limit_price) < order_price or order_price < entry_price:
                                            await helper.exchange.future.cancel_order(order["id"], _symbol)
                                            cancel_flag = True
                                    elif _side == "SELL":
                                        if float(limit_price) > order_price or order_price > entry_price:
                                            await helper.exchange.future.cancel_order(order["id"], _symbol)
                                            cancel_flag = True

                            if cancel_flag:
                                if _side == "BUY":
                                    response = await helper.exchange.future.create_limit_sell_order(
                                        _symbol, position_amt, limit_price
                                    )
                                    log(response)
                                elif _side == "SELL":
                                    response = await helper.exchange.future.create_limit_buy_order(
                                        _symbol, abs(position_amt), limit_price
                                    )
                                    log(response)
                        else:
                            is_future_open = False
                            futures = await helper.exchange.future.fetch_balance()
                            for future in futures["info"]["positions"]:
                                if float(future["positionAmt"]) != 0.0:
                                    if future["symbol"] == symbol_original.replace("/", ""):
                                        is_future_open = True
                                        break

                            if is_future_open:
                                if _side == "BUY":
                                    response = await helper.exchange.future.create_limit_sell_order(
                                        _symbol, position_amt, limit_price
                                    )
                                    log(response)
                                elif _side == "SELL":
                                    response = await helper.exchange.future.create_limit_buy_order(
                                        _symbol, abs(position_amt), limit_price
                                    )
                                    log(response)
                    except Exception as e:
                        _colorize_traceback(e)

            await spot_balance()
            log("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-", color="cyan")
            await asyncio.sleep(SLEEP_TIME)  # https://stackoverflow.com/a/61764275/2402577
        except ccxt.RequestTimeout as e:
            _colorize_traceback(e)
        except ccxt.DDoSProtection as e:
            _colorize_traceback(e)
        except ccxt.ExchangeNotAvailable as e:
            _colorize_traceback(e)
            print(f"[{type(e).__name__}]\n{str(e)[0:200]}")
        except ccxt.ExchangeError as e:
            _colorize_traceback(e)
        finally:
            await helper.exchange.future.close()
            await helper.exchange.spot.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(close())
    except Exception as e:
        _colorize_traceback(e)
        breakpoint()  # DEBUG
    finally:
        log("Program finished.", color="green")
