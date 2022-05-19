#!/usr/bin/env python3

# TODO: close short/logn position if you are in >%1 gain or
#       https://github.com/jaggedsoft/node-binance-api/ issue olarak sor

import math
import os
import pickle
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from binance.client import Client
from broker._utils.yaml import Yaml
from bs4 import BeautifulSoup
from dateutil.parser import parse
from utils import log, utc_to_local

HOME = Path.home()
SYMBOL = "GRTUSDT"

"""
https://python-binance.readthedocs.io/en/latest/account.html

At the current time Binance rate limits are:

1200 requests per minute
10 orders per second
100,000 orders per 24hrs

To run: nohup python -u ./binance_track.py > cmd.log &

Requirements:
python3 -m pip install python-binance
"""

# MAIN_ASSET = "BNB"
MAIN_ASSET = "BTC"
found_ones = []  # noqa
msg = []


ignore = [
    "SKL",
    "PROM",
    "HEGIC",
    "XVS",
    "SCRT",
    "ALPHA",
    "CTK",
    "AXS",
    "BOT",
    "AKRO",
    "HARD",
    "KP3RBNB",
    "REN",
    "RENBTC",
    "UNFI",
    "SLP",
    "CVP",
    "FOR",
    "SKL",
]
start = 0
TIME_TO_FORCE_BUY = 0.1
PERCENT_TO_BUY = 95


def get_futures_usd():
    futures_usd = 0.0
    for asset in client.futures_account_balance():
        name = asset["asset"]
        balance = float(asset["balance"])
        if name == "USDT":
            futures_usd += balance

        if name == "BNB":
            current_bnb_price_USD = client.get_symbol_ticker(symbol="BNBUSDT")["price"]
            futures_usd += balance * float(current_bnb_price_USD)

    return format(futures_usd, ".2f")


def percent_change(old, new, change):
    change = format(change, ".2f")
    pc = round((float(change)) / abs(old) * 100, 2)
    old = abs(old)
    print(f"from {format(old, '.2f')} to {format(float(old) + float(change), '.2f')} => ", end="")
    if pc > 0:
        log(f"{change} ({format(float(pc), '.2f')}%)", color="green", end="")
    else:
        log(f"{change} ({format(float(pc), '.2f')}%)", color="red", end="")
    return change, pc


def positions(_symbol=None):
    comm = futures_history(False, SYMBOL)
    comm = comm * 2
    comm = 0
    if _symbol:
        obj = client.futures_position_information(symbol=_symbol)
    else:
        obj = client.futures_position_information()

    # BUY = client.SIDE_BUY
    # SELL = client.SIDE_SELL
    # TYPE = client.ORDER_TYPE_STOP_LOSS_LIMIT
    # # # order_id = client.futures_get_all_orders(symbol="LTCUSDT")[-1]["clientOrderId"]
    # create_order = client.futures_create_order(symbol=_symbol, side=BUY, type=TYPE, stopPrice=80.0, closePosition='true')

    # client.futures_cancel_order(order_id)

    for future in obj:
        if (
            future["positionAmt"] != "0.0"
            and future["positionAmt"] != "0"
            and future["positionAmt"] != "0.00"
            and future["positionAmt"] != "0.000"
        ):
            # _bids = client.futures_order_book(symbol="XRPUSDT")["bids"][0][0]
            _asks = client.futures_order_book(symbol=future["symbol"])["asks"][0][0]
            _bids = client.futures_order_book(symbol=future["symbol"])["bids"][0][0]
            # TODO: add
            print(_bids)

            old_leverage = float(future["positionAmt"]) * float(future["entryPrice"])

            new = float(future["positionAmt"]) * float(_asks)  # TODO: short bids logs sa asks

            change = new - old_leverage
            _balance = format(float(get_futures_usd()) + float(change), ".2f")
            position_side = future["positionSide"]
            log(f"{_balance} ", "blue", end="")

            log(f"{future['marginType']}_{position_side} x{future['leverage']} ", color="yellow", end="")
            old_base = float(future["positionAmt"]) * float(future["entryPrice"]) / float(future["leverage"])
            old_base = old_base - comm
            old_new = old_base + change
            # _margin = float(future["isolatedMargin"]) + float(future["unRealizedProfit"]) * -1
            change, pc = percent_change(old_new, old_new, change)
            log(
                f" [ entry={future['entryPrice']}] [ asks={_asks} ] [ marked={future['markPrice']} ] ["
                f" liq={future['liquidationPrice']} ]",
                end="",
            )
            if abs(float(change)) > 2.0:
                log("ALERT", color="red", end="")
                log(f" comm={abs(comm)}")
            else:
                log(f" comm={abs(comm)}")
            log("\n")


def get_date(posix_time):
    ts = int(posix_time)
    return time.ctime(time.mktime(time.gmtime(ts / 1000)))


def the_sum(aList):
    s = 0
    for x in aList:
        if x > 0:
            s = s + x
    return s


def the_lost(aList):
    s = 0
    for x in aList:
        if x < 0:
            s = s + x
    return s


def futures_history(is_print=True, _symbol=None):
    _COMMISSON = 0
    commission_flag = False
    _sum = 0.0
    name_temp = "alper"
    _list = []
    commission = []
    latest_date = None
    _day = None
    dt = None
    daily_progress = 0.0
    # for future in client.futures_income_history(endTime="1606947505000", limit=1000):
    for future in client.futures_income_history(limit=1000):
        if future["symbol"] != name_temp:
            name_temp = future["symbol"]
            if future["symbol"] == "" and future["incomeType"] == "TRANSFER":
                pass
            else:
                daily_progress += _sum
                if _sum < 0:
                    if is_print:
                        log("%.8f" % _sum, color="red", end="")
                        print(
                            f" | {sum(_list)} COMMISSION={sum(commission)} | GAIN={the_sum(_list)}"
                            f" LOST={the_lost(_list)} ",
                            end="",
                        )
                        log(latest_date, "blue")
                else:
                    if is_print:
                        log("%.8f" % _sum, color="green", end="")
                        print(
                            f" | {sum(_list)} COMMISSION={sum(commission)} | GAIN={the_sum(_list)}"
                            f" LOST={the_lost(_list)} ",
                            end="",
                        )
                        log(latest_date, "blue")

                commission = []
                _list = []
                _sum = 0.0
                if is_print:
                    if is_print:
                        log(f"==> {name_temp} ", end="")

                if future["symbol"] == _symbol:
                    if is_print:
                        log(f"==> {name_temp} ", end="")
                    commission_flag = True

        if future["symbol"] != "" and future["incomeType"] != "TRANSFER":
            _sum += float(future["income"])
            if future["incomeType"] == "REALIZED_PNL" or future["incomeType"] == "INSURANCE_CLEAR":
                latest_date = get_date(future["time"])
                dt = parse(latest_date)
                local_dt = utc_to_local(dt)
                if local_dt.strftime("%d") != _day and is_print:
                    print("\033[A                             \033[A")  # To clear only a single line from the output
                    if daily_progress > 0:
                        log(f"===================> {daily_progress}     {dt.strftime('%d/%m/%Y')}", color="green")
                    else:
                        log(f"===================> {daily_progress}     {dt.strftime('%d/%m/%Y')}", color="red")

                    daily_progress = 0
                    log("\n" + local_dt.strftime("%d/%m/%Y"), "yellow")
                    log(f"==> {name_temp} ", end="")

                _day = local_dt.strftime("%d")
                _list.append(float(future["income"]))

            if future["incomeType"] == "COMMISSION":
                commission.append(float(future["income"]))

    if commission_flag:
        _COMMISSON = sum(commission)
        commission_flag = False
        if is_print:
            daily_progress += sum(_list)
            print(f" | {sum(_list)} COMMISSION={sum(commission)} | GAIN={the_sum(_list)} LOST={the_lost(_list)} ")

    daily_progress += _sum
    if _sum < 0:
        if is_print:
            log("%.8f " % _sum, color="red", end="")
            print(
                f" | {sum(_list)} COMMISSION={sum(commission)} | GAIN={the_sum(_list)} LOST={the_lost(_list)} ", end=""
            )
            log(latest_date, "blue")
    else:
        if is_print:
            log("%.8f" % _sum, color="green", end="")
            print(
                f" | {sum(_list)} COMMISSION={sum(commission)} | GAIN={the_sum(_list)} LOST={the_lost(_list)} ", end=""
            )
            log(latest_date, "blue")

    if is_print:
        if daily_progress > 0:
            log(f"===================> {daily_progress}     {dt.strftime('%d/%m/%Y')}", color="green")
        else:
            log(f"===================> {daily_progress}     {dt.strftime('%d/%m/%Y')}", color="red")
        log("")
    return _COMMISSON


def get_free_balance():
    free_asset = client.get_asset_balance(asset=MAIN_ASSET)["free"]
    free_asset = (float(free_asset) * PERCENT_TO_BUY) / 100
    print(f"free_{MAIN_ASSET}= %.8f" % free_asset)
    return free_asset


def sell_market(asset, symbol):
    free = client.get_asset_balance(asset=asset)["free"]

    order = client.order_market_sell(symbol=symbol, quantity=free)
    print(order)


def sell_limit(asset, symbol, price_to_sell):
    precision = 8
    price_to_sell = "{:0.0{}f}".format(price_to_sell, precision)
    free = client.get_asset_balance(asset=asset)["free"]
    order = client.order_limit_sell(symbol=symbol, price=str(price_to_sell), quantity=free)
    print(order)


def buy(_symbol):
    free_asset = get_free_balance()  # should be checked before each but attempt
    # _val_symbol = client.get_symbol_ticker(symbol=_symbol)
    # _val_price = _val_symbol["price"]  # market value usually higher in 3 ms
    _val_price = get_first_price(_symbol)
    print("price=" + str(_val_price))
    amount_to_buy = float(free_asset) / float(_val_price)
    amount_to_buy_floor = math.floor(amount_to_buy)

    amount = amount_to_buy
    precision = 2
    amount_str = "{:0.0{}f}".format(amount, precision)
    print(f"free_asset={free_asset}")
    print("amount_to_buy=" + str(amount_to_buy) + " | " + str(amount_str))
    print("amount_to_buy_floor=" + str(amount_to_buy_floor))
    # balance = free_asset
    # trades = client.get_recent_trades(symbol=_symbol)
    # quantity = (float(free_asset)) / float(trades[0]['price']) * 0.9995
    # _quantity = round(amount_to_buy, 2)
    # print("quantity=" + str(_quantity))
    order = "failed"
    if amount_str == 0.0 or amount_str == "0.00" or amount_str == "0.0":
        print("E: Account has insufficient balance for requested action")
        raise

    try:
        order = client.order_limit_buy(symbol=_symbol, price=str(_val_price), quantity=amount_str)
        print(order)
        return order
    except Exception as e:
        print(str(e))
        try:
            order = client.order_limit_buy(symbol=_symbol, price=str(_val_price), quantity=amount_to_buy_floor)
            print(order)
            return order
        except Exception as e:
            print(str(e))
    return order


def get_first_price(_symbol):
    first_price = 0
    agg_trades = client.aggregate_trade_iter(symbol=_symbol, last_id=0)
    # agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="60 minutes ago UTC")
    flag = False
    for trade in agg_trades:
        print(trade)
        if flag:
            if first_price > trade["p"]:
                print("Second price is smaller may decrease abort mission")
                sys.exit(1)
            else:
                return first_price
        else:
            first_price = trade["p"]
            flag = True


def telegram_msg(_found, _receipt=""):
    global start
    end = time.time()
    if end - start > 30:
        if start > 0:
            print("## Attempting to send telegram message")
        _mail = "\n".join(msg)
        _mail = str(_found) + "\nbinance_symbols@" + str(found_ones) + "\n" + _mail
        subprocess.call([f"{HOME}/venv/bin/telegram-send", str(_mail) + "\n---------\n" + str(_receipt)])
        start = time.time()


def find_between(s, start, end):
    try:
        _lst = []
        lst = re.findall(r"\((.*?)\)", s)
        if lst:
            if "List" in s:
                _lst.append(lst[0])
                msg.append(s)

        for one in _lst:
            found_ones.append(one) if one not in found_ones else found_ones
    except:
        return None


def save_obj(name):
    _file = f"{HOME}/.binance/{name}.pk"
    # if not os.path.exists(_file):
    #     with open(_file, 'w'):
    #         pass

    _balances = balances["balances"]
    syms = {}
    for balance in _balances:
        syms[balance["asset"]] = True

    # if not os.path.exists(_file):
    #     os.makedirs(f"{HOME}/.binance")

    with open(_file, "wb") as f:
        pickle.dump(syms, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    _file = f"{HOME}/.binance"
    if not os.path.exists(_file):
        with open(_file, "w"):
            pass

    with open(_file + "/" + name + ".pkl", "rb") as f:
        return pickle.load(f)


def check_url(url):
    # response = urlopen(url).read()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95"
            " Safari/537.36"
        )
    }

    # download the homepage
    _response = requests.get(url, headers=headers)
    soup = BeautifulSoup(_response.text, "lxml")
    announcements = soup.find_all("a", {"class": "css-1neg3js"})  #
    for ann in announcements:
        announcement = ann.text.strip()
        find_between(announcement, "(", ")")


def run():
    _balances = balances["balances"]
    syms = {}
    for balance in _balances:
        syms[balance["asset"]] = True
        # print(balance["asset"])

    url = "https://www.binance.com/en/support/announcement/c-48"
    check_url(url)

    url = "https://www.binance.com/en/support/announcement/c-49"
    check_url(url)
    print(found_ones)
    _receipt = "upps"
    found_flag = False
    flag = False
    f_ones = []
    for found in found_ones:
        if found not in ignore:
            try:
                org_symbols[found]
            except:
                flag = True
                output = ""
                try:
                    if "BTC" in found:  # may shown as RENBTC
                        _symbol = found
                    else:
                        _symbol = f"{found}{MAIN_ASSET}"

                    while True:
                        if not found_flag:
                            print("found_symbol=" + _symbol)

                        try:
                            output = client.get_symbol_ticker(symbol=_symbol)
                            _receipt = buy(_symbol)
                            print(_receipt)
                            bought_price = _receipt["fills"][0]["price"]
                            print("bought_price=" + bought_price)
                            price_to_sell_float = 5.0 * float(bought_price) / float(4.0)
                            price_to_sell = "{0:.10f}".format(price_to_sell_float)
                            print(f"price_to_sell={price_to_sell}")
                            try:
                                _receipt = sell_limit(found, _symbol, price_to_sell_float)
                                print(_receipt)
                            except:
                                pass

                            break
                        except Exception as e:
                            # print("E: " + str(e))
                            if "Invalid symbol." in str(e) and not found_flag:
                                print("E: " + str(e))
                            else:
                                print("_ ", end="", flush=True)

                            found_flag = True
                            try:
                                telegram_msg(str(f_ones), "ALERT")
                            except:
                                pass
                            time.sleep(TIME_TO_FORCE_BUY)
                except:
                    pass

                print("found:" + found + " => " + str(output))
                f_ones.append(found)

    if flag:
        while True:
            try:
                telegram_msg(str(f_ones), _receipt)
            except:
                pass
            time.sleep(60)


if __name__ == "__main__":
    print("To run: nohup python -u ./binance_track.py > cmd.log & \n")
    HOME = Path.home()
    _cfg = Yaml(HOME / ".binance.yaml")
    api_key = str(_cfg["b"]["key"])
    api_secret = str(_cfg["b"]["secret"])
    client = Client(api_key, api_secret)
    # try:
    #     details = client.get_max_margin_transfer(asset="BTC")
    #     print(client.get_all_margin_orders())
    #     print(details)
    #     # print(client.futures_account_balance())
    # except:
    #     pass

    try:
        balances = client.get_account()
    except requests.exceptions.ConnectionError:
        log("ConnectionError", color="red")
        sys.exit()
    print(client.get_asset_balance(asset=MAIN_ASSET))
    info = client.get_account()
    free_asset = get_free_balance()

    # margin =====
    # print(client.get_open_margin_orders(symbol='ETHBTC'))
    # for d in client.get_margin_account()['userAssets']:
    #     if d['free'] != "0":
    #         print(d)

    # ua = {d['asset']: d for d in data['userAssets']}
    # print(ua['BTC']['free'])
    # ============

    ignore_list = ["EON", "ADD", "MEETONE", "ATD", "EOP"]
    total = 0
    sum_btc = 0.0
    for _balance in balances["balances"]:
        asset = _balance["asset"]
        if float(_balance["free"]) != 0.0 and asset not in ignore_list:
            try:
                if asset == "BTC":
                    sum_btc += float(_balance["free"])
                else:
                    _price = client.get_symbol_ticker(symbol=asset + "BTC")
                    sum_btc += float(_balance["free"]) * float(_price["price"])
            except:
                pass

    current_btc_price_USD = client.get_symbol_ticker(symbol="BTCUSDT")["price"]
    current_btc_price_TRY = client.get_symbol_ticker(symbol="BTCTRY")["price"]
    current_btc_price = client.get_symbol_ticker(symbol="BTCUSDT")["price"]

    futures_usd = get_futures_usd()
    print(f"Futures ==> {futures_usd} USD")

    own_usd = 0.0
    own_usd = sum_btc * float(current_btc_price_USD)
    own_try = sum_btc * float(current_btc_price_TRY)
    print("Spot => %.8f BTC == " % sum_btc, end="")
    print("%.8f USD == " % own_usd, end="")
    print("%.8f TRY" % own_try)

    print(f"overview => {float(own_usd) + float(futures_usd)} USD")

    for asset in client.futures_account_balance():
        name = asset["asset"]
        balance = asset["balance"]

    futures_history()
    while True:
        time.sleep(0.1)
        positions(SYMBOL)

    # sys.exit()

    # save_obj("symbols")
    # sys.exit()

    try:
        org_symbols = load_obj("symbols")
    except:
        save_obj("symbols")

    _date = datetime.datetime.now().strftime("%I:%M%p %B %d %Y")
    try:
        telegram_msg(f"Started ... {_date}")
    except:
        pass

    SLEEP_DURATION = 45
    while True:
        run()
        _date = datetime.datetime.now().strftime("%I:%M%p %B %d %Y")
        print(_date)
        msg = []
        time.sleep(SLEEP_DURATION)
