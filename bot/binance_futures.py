#!/usr/bin/env python3

from broker._utils._log import log
from broker._utils.tools import _date, percent_change
from contextlib import suppress
from filelock import FileLock

from bot import cfg, helper
from bot.bot_helper_async import TP
from bot.bot_helper_async_usdt import BotHelperSpotAsync
from bot.config import config
from bot.spot_lib import cancel_check_orders, new_order, update_spot_timestamp

bot_async = BotHelperSpotAsync()


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
                limit_price = f"{float(entry_price) * TP.get_profit_amount(isolated_wallet):.{precision}f}"
            else:
                log("==> ", "green", end="")
                side = "BUY"
                change = price - entry_price
                limit_price = f"{float(entry_price) * TP.get_profit_amount(isolated_wallet):.{precision}f}"

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
                log(f"warning: calc_locked={per}% ", end="")

            if isolated_wallet > config.discord_msg_above_usdt:
                await channel.send(
                    f"{asset} isolated_wallet={int(isolated_wallet)}, "
                    f"unrealized_profit={unrealized_profit}({format(asset_percent_change, '.2f')}%)",
                    delete_after=cfg.SLEEP_INTERVAL,
                )

            if (
                isolated_wallet < config.isolated_wallet_limit
                and asset_percent_change <= config.USDTPERP_PERCENT_CHANGE_TO_ADD
            ):
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal)
            elif isolated_wallet > config.isolated_wallet_limit and asset_percent_change <= -10.0 and float(per) < 30.0:
                # when isolated_wallet is greater than isolated_wallet_limit (~100$)
                await new_order(symbol, side, position_amt, isolated_wallet, usdt_bal, mul=1, per=50.0)

            await cancel_check_orders(symbol, limit_price, side, entry_price, position_amt)

    if total_lost > 0.0125:
        log(f"lost={format(total_lost, '.2f')}$", "bold red")

    with FileLock(config.status.fp_lock, timeout=5):
        if config.status_usdtperp["count"] != count:
            config.status_usdtperp["count"] = count

        if not isinstance(config.status["log"]["futures"]["max_position_count"], int):
            config.status["log"]["futures"]["max_position_count"] = 0

        if count > config.status["log"]["futures"]["max_position_count"]:
            config.status["log"]["futures"]["max_position_count"] = count

    return print_flag


def future_stats(usdt_bal, unix_timestamp_ms):
    with FileLock(config.status.fp_lock, timeout=5):
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
    log(f"{_date().replace('2021-','')} {unix_timestamp_ms}", "yellow", is_write=is_write)


def futures_bal(info, asset) -> float:
    return float(bot_async.futures_balance[info][asset])
