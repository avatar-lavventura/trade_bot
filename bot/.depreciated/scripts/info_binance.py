#!/usr/bin/env python3

import json
import math
import os
import pickle
import re
import subprocess
import sys
import time
import urllib  # the lib that handles the url stuff
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from binance.client import Client
from broker._utils.yaml import Yaml
from bs4 import BeautifulSoup

HOME = str(Path.home())
balances = None

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
]
start = 0
TIME_TO_FORCE_BUY = 0.1
PERCENT_TO_BUY = 95


def get_all_prices(_symbol):
    first_price = 0
    agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="60 minutes ago UTC")
    # agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="1 day ago UTC")
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
    if amount_str in (0.0, "0.00", "0.0"):
        raise Exception("E: Account has insufficient balance for requested action")

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
    agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="60 minutes ago UTC")
    # agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="1 day ago UTC")
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
        lst = re.findall(r"\((.*?)\)", s)
        if lst:
            msg.append(s)

        for one in lst:
            found_ones.append(one) if one not in found_ones else found_ones
    except:
        return None


def save_obj(name):
    _dir = HOME + "/.binance"
    _balances = balances["balances"]
    syms = {}
    for balance in _balances:
        syms[balance["asset"]] = True

    if not os.path.exists(_dir):
        os.makedirs(_dir)

    with open(_dir + "/" + name + ".pkl", "wb") as f:
        pickle.dump(syms, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    _dir = HOME + "/.binance"
    with open(_dir + "/" + name + ".pkl", "rb") as f:
        return pickle.load(f)


def _check_url(url):
    # response = urlopen(url).read()
    data = urllib.request.urlopen(url)  # it's a file like object and works just like a file
    for line in data:  # files are iterable
        if "Will Delist" in line.decode("utf-8"):
            _line = line.decode("utf-8")
            result = re.search("Delisting(.*)catalogs", _line)
            ralper = result.group(0)
            d = ralper.split('"title"')
            for myline in d:
                try:
                    rrr = re.search(':"(.*)type', myline)
                    output = rrr.group(0)
                    output = output.replace(':"', "").replace('","type', "")
                    print(output)
                except:
                    pass


def check_url(url):
    # response = urlopen(url).read()
    data = urllib.request.urlopen(url)  # it's a file like object and works just like a file
    for line in data:  # files are iterable
        if "Will Delist" in line.decode("utf-8"):
            _line = line.decode("utf-8")
            result = re.search("Delisting(.*)catalogs", _line)
            ralper = result.group(0)
            d = ralper.split('"title"')
            for myline in d:
                try:
                    rrr = re.search(':"(.*)type', myline)
                    output = rrr.group(0)
                    output = output.replace(':"', "").replace('","type', "")
                    print(output)
                except:
                    pass

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95"
            " Safari/537.36"
        )
    }

    # # download the homepage
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")
    # soup.find_all('a')
    announcements = soup.find_all("a", {"class": "css-1txs1yu"})  #
    breakpoint()  # DEBUG
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
                # org_symbols[found]
                pass
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
                            print("price_to_sell=" + str(price_to_sell))
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
    # url = "https://www.binance.com/en/support/announcement/c-49"
    url = "https://www.binance.com/en/support/announcement/delisting?c=161&navId=161"
    print(f"Link={url}\n")
    _check_url(url)
