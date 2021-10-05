#!/usr/bin/env python3

# TODO: symbol check when new position is created with different symbol, apply
#       when there is no positon at the moment
# TODO:if <0% put a sell limit at entry price (resque)
# TODO: firefox'da dene daha hizli olabilir
# TODO: put stop-loss right away
# TODO: l= latest price fetch wrong // check fetch price sometimes wrong value is obtained
# TODO: check real occured leverage value
# TODO: >3% profit put take-profit or trailing stop no matter what and always close the position in gain
# TODO: For now play with 2x at max or 1x (normal).
# TODO: Fetch signals and if line is red alert for reverse position or visa versa

import sys
import time

from dateutil.parser import parse
from ebloc_broker.broker._utils.tools import (
    _percent_change,
    log,
    percent_change,
    print_tb,
    timestamp_to_local,
    utc_to_local,
)
from forex_python.converter import CurrencyRates

c = CurrencyRates()
TOTAL_BALANCE = 1000
_arrow = "=============="
arrow_in = _arrow + ">"
arrow_out = "<" + _arrow


def get_date(posix_time):
    return time.ctime(time.mktime(time.gmtime(int(posix_time) / 1000)))


def the_lost(aList):
    s = 0
    for x in aList:
        if x < 0:
            s = s + x
    return s


def get_color(color):
    if color > 0:
        return "green"
    else:
        return "red"


def futures_history(binance, _symbol=None):
    client = binance.client
    name_temp = "hello_world"
    _COMMISSON = 0
    commission_flag = False
    _sum = 0.0
    counter = 0
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
            log(f"E: {e}", "red")
            sys.exit(1)

        print_tb()
        log("==> Sleeping for 15 seconds")
        time.sleep(15)
        return

    for future in history_log:
        if future["symbol"] != name_temp and "eksi" not in future["info"]:
            name_temp = future["symbol"]
            if future["symbol"] == "" and future["incomeType"] == "TRANSFER":
                pass
            else:
                counter += 1
                _sum = _sum - sum(commission)
                daily_progress += _sum
                _color = get_color(_sum)
                _pad = ""
                if _sum >= 0:
                    _pad = " "

                if _sum != 0.0:
                    log(f"{_pad}%.4f" % _sum, _color, end="")
                    _lost_value = the_lost(_list)
                    if _lost_value == 0.00:
                        log(f" | COMM={format(sum(commission), '.4f')} ", end="")
                    else:
                        log(f" | COMM={format(sum(commission), '.4f')} ", end="")
                        log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", "red", end="")

                    log(f" {latest_time} ", "yellow")

                _name = "{:<9}".format(name_temp)
                if _sum != 0.0:
                    log(f"==> {_name.replace('USDT', '')} ", end="")

                commission = []
                _list = []
                _sum = 0.0

        if future["symbol"] != "" and future["incomeType"] != "TRANSFER":
            _sum += float(future["income"])
            if future["incomeType"] in ["REALIZED_PNL", "INSURANCE_CLEAR"]:
                latest_date = get_date(future["time"])
                dt = parse(latest_date)
                local_dt = utc_to_local(dt)
                latest_time = local_dt.strftime("%H:%M:%S")
                if local_dt.strftime("%d") != _day:
                    if daily_progress != 0.0:
                        print("will be deleted", end="\r")

                    _color = get_color(daily_progress)
                    if daily_progress != 0.0:
                        _daily_progress = format(daily_progress, ".2f")
                        log(f"{arrow_in} {_daily_progress}$ {arrow_out} | ", _color, end="")
                        log(f"{format(100.0 * float(_daily_progress) / TOTAL_BALANCE, '.2f')}% ", _color, end="")
                        log(counter)

                    daily_progress = 0
                    counter = 0
                    _name = "{:<9}".format(name_temp)
                    log("\n" + local_dt.strftime("%d/%m/%Y %A"), "cyan")
                    log(f"==> {_name.replace('USDT', '')} ", end="")

                _day = local_dt.strftime("%d")

            try:
                commission.append(comm_dict[future["tradeId"]])
            except:
                pass

    if commission_flag:
        _COMMISSON = sum(commission)
        commission_flag = False
        daily_progress += sum(_list)
        _lost_value = the_lost(_list)
        if _lost_value == 0.00:
            log(f" | COMM={format(sum(commission), '.4f')} ", end="")
        else:
            log(f" | COMM={format(sum(commission), '.4f')} ", end="")
            log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", "red", end="")

    _sum = _sum - sum(commission)
    daily_progress += _sum
    _color = get_color(_sum)
    if _sum > 0.0:
        log(f" {format(_sum, '.4f')}", _color, end="")
    else:
        log(f"{format(_sum, '.4f')}", _color, end="")

    _lost_value = the_lost(_list)
    if daily_progress != 0.0:
        if _lost_value == 0.00:
            log(f" | COMM={format(sum(commission), '.4f')} ", end="")
        else:
            log(f" | COMM={format(sum(commission), '.4f')} ", end="")
            log(f"LOST={format(abs(the_lost(_list)), '.4f')} ", "red", end="")

    log(f" {latest_time}", "yellow")
    _color = get_color(daily_progress)
    _daily_progress = format(daily_progress, ".2f")
    log(f"{arrow_in} {_daily_progress}$ {arrow_out} | ", _color, end="")
    log(f"{format(100.0 * float(_daily_progress) / TOTAL_BALANCE, '.2f')}% ", _color, end="")
    log(counter + 1)
    log("")
    return _COMMISSON, latest_symbol_income, daily_progress, funding_dict


def positions(client, latest_symbol_income, daily_progress, _symbol=None):
    START_POSITION = False
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
            if float(future["isolatedMargin"]) != 0.0:
                _margin = float(future["isolatedMargin"]) + float(future["unRealizedProfit"]) * -1
            else:
                _margin = float(future["positionAmt"]) * float(future["entryPrice"]) / float(future["leverage"])

            old_leverage = float(future["positionAmt"]) * float(future["entryPrice"])
            new = float(future["positionAmt"]) * float(price_to_consider)
            change = new - old_leverage
            if not START_POSITION:
                log(f"{_symbol} ", "cyan", end="")
                log(f"{future['marginType']} ", "yellow", end="")
                if future["entryPrice"] > future["liquidationPrice"]:
                    log(f"Lx{future['leverage']} ", "green", end="")
                else:
                    log(f"Sx{future['leverage']} ", "red", end="")

                log(f"COMM={latest_symbol_income}", "blue", end="")
                _s = _symbol.replace("USDT", "") + "BTC"
                _btc_price = int(float(client.get_symbol_ticker(symbol="BTCUSDT")["price"]))
                _token_price = float(client.get_symbol_ticker(symbol=_s)["price"])
                _token_price = format(_token_price, ".8f")
                log(f" | BTCUSDT={_btc_price} {_s}={_token_price} | ", end="")
                START_POSITION = True
                if daily_progress > 0.0:
                    log(f"dp={format(daily_progress, '.2f')}$", "green")
                else:
                    log(f"dp={format(daily_progress, '.2f')}$", "red")

            marked = format(float(future["markPrice"]), ".6f")
            change = format(change, ".8f")
            pc = percent_change(_margin, change, end="")
            log(" [ e=", end="")
            log(future["entryPrice"], "cyan", end="")
            log(f" p={price_to_consider} m={marked} l={future['liquidationPrice']} ]", end="")
            real_pc = _percent_change(float(future["entryPrice"]), price_to_consider)
            _real_pc = format(real_pc, ".2f")
            log(f" {_real_pc}%", end="")
            if not real_pc == 0.0:
                _leverage = round(abs(pc / real_pc))
                log(f" x{_leverage}")
            else:
                log("")

            return True
    return False
