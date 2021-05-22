#!/usr/bin/env python3

# TODO: symbol check when new position is created with different symbol, apply
#       when there is no positon at the moment
# TODO:if <0% put a sell limit at entry price (resque)
# TODO: before each order cancell all orders try/catch
# TODO: firefox'da dene daha hizli olabilir
# TODO: put stop-loss right away
# TODO: l= latest price fetch wrong // check fetch price sometimes wrong value is obtained
# TODO: check real occured leverage value
# TODO: >3% profit put take-profit or trailing stop no matter what and always close the position in gain
# TODO: For now play with 2x at max or 1x (normal).
# TODO: Fetch signals and if line is red alert for reverse position or visa versa

import sys
import time
from decimal import Decimal

from dateutil.parser import parse
from forex_python.converter import CurrencyRates
from tools import _colorize_traceback, log, timestamp_to_local, utc_to_local

from libs.math import _percent_change, percent_change

c = CurrencyRates()

GAIN_LIMIT = 10
START_POSITION = False

_arrow = "========================="
arrow_in = _arrow + ">"
arrow_out = "<" + _arrow


def add_one(v: float):
    v = float(v)
    after_comma = Decimal(v).as_tuple()[-1] * -10
    add = Decimal(1) / Decimal(10 ** after_comma)
    return Decimal(v) + add


def gain_control(pc, side, future, client, symbol, price_to_consider, comm=0):
    amount = future["positionAmt"]
    if float(pc) >= GAIN_LIMIT:
        if side == "LONG":
            create_order = client.futures_create_order(
                symbol=symbol,
                side="SELL",
                type="LIMIT",
                timeInForce="GTC",
                quantity=abs(float(amount)),
                price=price_to_consider,
            )
            print(create_order)
            sys.exit(1)
        else:
            create_order = client.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="LIMIT",
                timeInForce="GTC",
                quantity=abs(float(amount)),
                price=price_to_consider,
            )
            print(create_order)
            sys.exit(1)


def save_me(pc, side, future, client, symbol, SAVE_LIMIT, comm=0):
    amount = abs(float(future["positionAmt"]))
    if pc < 0:
        if abs(float(pc)) > SAVE_LIMIT:
            log("!!!ALERT!!!", color="red", end="")
            log(f" comm={abs(comm)}")
            if side == "LONG":
                create_order = client.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=amount)
            else:
                create_order = client.futures_create_order(symbol=symbol, side="BUY", type="MARKET", quantity=amount)

            print(create_order)
            # sys.exit(1)
        else:
            pass
            # log(f" comm={abs(comm)}")


def get_date(posix_time):
    ts = int(posix_time)
    return time.ctime(time.mktime(time.gmtime(ts / 1000)))


def the_lost(aList):
    s = 0
    for x in aList:
        if x < 0:
            s = s + x
    return s


def the_sum(aList):
    s = 0
    for x in aList:
        if x > 0:
            s = s + x
    return s


def futures_history(client, _symbol=None):
    name_temp = "hello_world"
    # _lira = c.get_rate("USD", "TRY")  # TODO: halts once in a while
    _lira = 1
    _COMMISSON = 0
    commission_flag = False
    _sum = 0.0
    _list = []
    commission = []
    comm_dict = {}
    funding_dict = {}
    latest_date = None
    latest_time = None
    _day = None
    dt = None
    daily_progress = 0.00
    try:
        history_log = client.futures_income_history(limit=1000, incomeType="REALIZED_PNL")
        history_log_comms = client.futures_income_history(limit=1000, incomeType="COMMISSION")
        history_log_fundings = client.futures_income_history(limit=1000, incomeType="FUNDING_FEE")

        for history_log_comm in history_log_comms:
            comm_dict[history_log_comm["tradeId"]] = abs(float(history_log_comm["income"]))

        for history_log_funding in history_log_fundings:
            _date = timestamp_to_local(int(history_log_funding["time"]))
            funding_dict[history_log_funding["symbol"]] = [float(history_log_funding["income"]), _date]

        latest_position = client.futures_income_history(limit=1, incomeType="COMMISSION")[0]
        try:
            _symbol = latest_position["symbol"]
            client.futures_position_information(symbol=_symbol)
        except:
            pass
        latest_symbol_income = abs(float(latest_position["income"]))
    except Exception as e:
        if "Invalid API-key" in str(e):
            log(f"E: {e}", color="red")
            sys.exit(1)

        _colorize_traceback()
        log("==> Sleeping for 15 seconds")
        time.sleep(15)
        return

    for future in history_log:
        if future["symbol"] != name_temp and "eksi" not in future["info"]:
            name_temp = future["symbol"]
            if future["symbol"] == "" and future["incomeType"] == "TRANSFER":
                pass
            else:
                _sum = _sum - sum(commission)
                daily_progress += _sum
                if _sum < 0:
                    _color = "red"
                else:
                    _color = "green"

                _pad = ""
                if _sum >= 0:
                    _pad = " "

                if _sum != 0.0:
                    log(f"{_pad}%.8f" % _sum, color=_color, end="")
                    value = sum(_list)
                    _lost_value = the_lost(_list)
                    if _lost_value == 0.00:
                        log(
                            f" | {_pad}{format(value, '.4f')} COMM={format(sum(commission), '.4f')} | "
                            f"GAIN={format(the_sum(_list), '.4f')} ",
                            end="",
                        )
                    else:
                        log(
                            f" | {_pad}{format(value, '.4f')} COMM={format(sum(commission), '.4f')} |"
                            f" GAIN={format(the_sum(_list), '.4f')} ",
                            end="",
                        )
                        log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", color="red", end="")
                    log(latest_time, "blue")

                _name = "{:<9}".format(name_temp)
                if _sum != 0.0:
                    log(f"==> {_name} ", end="")

                commission = []
                _list = []
                _sum = 0.0

                # if future["symbol"] == _symbol:
                #     _name = "{:<9}".format(name_temp)
                #     log(f"==> {_name} ", end="")
                #     commission_flag = True

        if future["symbol"] != "" and future["incomeType"] != "TRANSFER":
            _sum += float(future["income"])
            if future["incomeType"] in ["REALIZED_PNL", "INSURANCE_CLEAR"]:
                latest_date = get_date(future["time"])
                dt = parse(latest_date)
                local_dt = utc_to_local(dt)
                latest_time = local_dt.strftime("%H:%M:%S")
                if local_dt.strftime("%d") != _day:
                    lira = float(daily_progress) * float(_lira)
                    if daily_progress != 0.0:
                        print("This is the message that will be deleted", end="\r")

                    if daily_progress > 0:
                        _color = "green"
                    else:
                        _color = "red"

                    if daily_progress != 0.0:
                        log(
                            f"{arrow_in} {format(daily_progress, '.2f')}$ {format(lira, '.2f')}"
                            f" TRY {arrow_out} {dt.strftime('%d/%m/%Y')}",
                            color=_color,
                        )

                    daily_progress = 0
                    log("\n" + local_dt.strftime("%d/%m/%Y %A"), color="yellow")

                    _name = "{:<9}".format(name_temp)
                    log(f"==> {_name} ", end="")

                _day = local_dt.strftime("%d")
                _list.append(float(future["income"]))
                # if float(future["income"]) > 0:
                #     log(float(future["income"]), color="green") ## delete
                # else:
                #     log(float(future["income"]), color="red") ## delete

            try:
                commission.append(comm_dict[future["tradeId"]])
            except:
                pass

            # if future["incomeType"] == "COMMISSION":
            #     commission.append(float(future["income"]))

    if commission_flag:
        _COMMISSON = sum(commission)
        commission_flag = False
        daily_progress += sum(_list)
        _lost_value = the_lost(_list)
        if _lost_value == 0.00:
            log(
                f" | {format(sum(_list), '.4f')} COMM={format(sum(commission), '.4f')} | "
                f"GAIN={format(the_sum(_list), '.4f')} ",
                end="",
            )
        else:
            log(
                f" | {format(sum(_list), '.4f')} COMM={format(sum(commission), '.4f')} |"
                f" GAIN={format(the_sum(_list), '.4f')} ",
                end="",
            )
            log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", color="red", end="")

    _sum = _sum - sum(commission)
    daily_progress += _sum
    if _sum < 0:
        _color = "red"
    else:
        _color = "green"

    if _sum > 0.0:
        log(f" {format(_sum, '.8f')}", color=_color, end="")
    else:
        log(f"{format(_sum, '.8f')}", color=_color, end="")

    value = sum(_list)
    _lost_value = the_lost(_list)
    if daily_progress != 0.0:
        if _lost_value == 0.00:
            log(
                f" | {format(value, '.4f')} COMM={format(sum(commission), '.4f')} |"
                f" GAIN={format(the_sum(_list), '.4f')} ",
                end="",
            )
        else:
            log(
                f" | {format(value, '.4f')} COMM={format(sum(commission), '.4f')} |"
                f" GAIN={format(the_sum(_list), '.4f')} ",
                end="",
            )
            log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", color="red", end="")

    log(latest_time, color="blue")

    lira = float(daily_progress) * float(_lira)
    if daily_progress > 0:
        _color = "green"
    else:
        _color = "red"

    log(
        f"{arrow_in} {format(daily_progress, '.2f')}$ {format(lira, '.2f')} TRY {arrow_out} {dt.strftime('%d/%m/%Y')} ",
        color=_color,
    )
    log("")
    return _COMMISSON, latest_symbol_income, daily_progress, funding_dict


def get_futures_usd(client, is_both=True):
    futures_usd = 0.0
    for asset in client.futures_account_balance():
        name = asset["asset"]
        balance = float(asset["balance"])
        if name == "USDT":
            futures_usd += balance

        if name == "BNB" and is_both:
            current_bnb_price_USD = client.get_symbol_ticker(symbol="BNBUSDT")["price"]
            futures_usd += balance * float(current_bnb_price_USD)

    return format(futures_usd, ".2f")


def positions(client, latest_symbol_income, daily_progress, _symbol=None):
    global START_POSITION
    if _symbol:
        obj = client.futures_position_information(symbol=_symbol)
    else:
        obj = client.futures_position_information()

    price_to_consider = None
    for future in obj:
        if future["positionAmt"] not in ["0.0", "0", "0.00", "0.000", "0.000"]:
            if not _symbol:
                _symbol = future["symbol"]
            # _bids = client.futures_order_book(symbol="XRPUSDT")["bids"][0][0]
            # _asks = client.futures_order_book(symbol=future["symbol"])["asks"][0][0]
            # _bids = client.futures_order_book(symbol=future["symbol"])["bids"][0][0]  # TODO: add
            price_to_consider = client.futures_symbol_ticker(symbol=future["symbol"])["price"]
            if not float(future["isolatedMargin"]) == 0.0:
                _margin = float(future["isolatedMargin"]) + float(future["unRealizedProfit"]) * -1
            else:
                _margin = float(future["positionAmt"]) * float(future["entryPrice"]) / float(future["leverage"])

            old_leverage = float(future["positionAmt"]) * float(future["entryPrice"])
            new = float(future["positionAmt"]) * float(price_to_consider)
            change = new - old_leverage
            if not START_POSITION:
                log(f"{_symbol} ", color="cyan", end="")
                log(f"{future['marginType']} ", color="yellow", end="")
                if future["entryPrice"] > future["liquidationPrice"]:
                    log(f"Lx{future['leverage']} ", color="green", end="")
                else:
                    log(f"Sx{future['leverage']} ", color="red", end="")

                log(f"COMM={latest_symbol_income}", color="blue", end="")
                _s = _symbol.replace("USDT", "") + "BTC"
                _btc_price = int(float(client.get_symbol_ticker(symbol="BTCUSDT")["price"]))
                _token_price = float(client.get_symbol_ticker(symbol=_s)["price"])
                _token_price = format(_token_price, ".8f")
                log(f" | BTCUSDT={_btc_price} {_s}={_token_price} | ", end="")
                START_POSITION = True
                if daily_progress > 0.0:
                    log(f"dp={format(daily_progress, '.2f')}$", color="green")
                else:
                    log(f"dp={format(daily_progress, '.2f')}$", color="red")

            _balance = format(float(get_futures_usd(client)) + float(change), ".4f")
            if float(_balance) > 0.0:
                _lira = 1
                # _lira = c.get_rate("USD", "TRY")
                lira = float(_balance) * float(_lira)
                lira = format(lira, ".2f")

            marked = format(float(future["markPrice"]), ".6f")
            change = format(change, ".8f")
            pc = percent_change(_margin, change, end="")
            log(" [ e=", end="")
            log(future["entryPrice"], color="cyan", end="")
            log(f" p={price_to_consider} m={marked} l={future['liquidationPrice']} ]", end="")

            real_pc = _percent_change(float(future["entryPrice"]), price_to_consider)
            _real_pc = format(real_pc, ".2f")
            log(f" {_real_pc}%", end="")
            if not real_pc == 0.0:
                _leverage = round(abs(pc / real_pc))
                log(f" x{_leverage}")
            else:
                log("")

            # log(f" ({lira} TRY)", color="blue")
            # save_me(pc, side, future, client, _symbol, SAVE_LIMIT=50)
            # gain_control(pc, side, future, client, _symbol, price_to_consider)
            return True
    return False
