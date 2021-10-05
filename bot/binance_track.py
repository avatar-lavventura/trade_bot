#!/usr/bin/env python3
#
# TODO: add 1 price change affect on percent
#       0.32 to 0.33 (its percent change affect on usdt price)
# TODO: shown BTCUSDT price, grieen on rise red on drop  percent change maybe
# TODO: show BTC - symbol price , grieen on rise red on drop
# TODO: >5 gain limit entry no matter what and trail the rise
#         artiya gecersen hic bir kosulda eksiye kapama kitlenip kaliyorsun
# TODO: eksidesin uzun sure yesil oldu , > %10 kazanc olursa  ,
#       %1e stop limit koy ne olur ne olmaz, kara girdiysen eksiye dusmesine izin verme

# TODO: close short/logn position if you are in >%1 gain or
#       https://github.com/jaggedsoft/node-binance-api/ issue olarak sor
# sadece price"i arka planda daha hizli cek
#
# TODO: is open position?
# You can use position
# information. Pull datas by futures_position_information() as
# dataframe and then filter the positionAmt column . You must
# change type of column as float then filter != '0' ones.
#
# # BEFORE TREDE:
# > NEVER trade if you are drunk (had alcohol)
# > KAYIP yasadigin kagida inat edip o gun bir daha girme
# TAKE PROFIT no matter what if you are in gain
# ANNEN yanindayken be moralsizsen alis yapma
#
# 12 den sonra modafinil aldiysan al sat yapma zombie olup kitleniyorsun ve cok
# buyuk zararlar yaratiyorsun kedine. 10$ oluyor 140$ inatlasip pozisyon
# buyuyunce de zarar da buyumus oluyor. Modafinil etkisi ile de kitlenip
# kaliyorsun
#
# Funding fee den sonra dusucek diye akillilip edip shortlama seni ters kosede
# birakabilir. Hele grafige bakmadan yaparsan husran ile sonuclanabilir
# https://python-binance.readthedocs.io/en/latest/account.html

import argparse
import math
import os
import pickle
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from bot.python_binance import Python_Binance
import binance_lib
import requests
from binance_lib import futures_history, positions
from bs4 import BeautifulSoup
from ebloc_broker.broker._utils import _log
from bot.user_setup import check_binance_obj
from ebloc_broker.broker._utils.tools import log, run

HOME = str(Path.home())
_log.ll.LOG_FILENAME = "progress.log"
_log.ll.IS_PRINT = False

SEP = "====================================================================================="
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95"
        " Safari/537.36"
    )
}

MAIN_ASSET = "BTC"  # "BNB"
SLEEP_DURATION = 45
ignore_balance_list = ["EON", "ADD", "MEETONE", "ATD", "EOP"]
start = 0
TIME_TO_FORCE_BUY = 0.1
PERCENT_TO_BUY = 95
SYMBOL = None
FUTURE_AMOUNT_TO_TRADE = 2000
client = None
client_helper = None
found_ones = []  # noqa
msg = []
org_symbols = {}
parser = argparse.ArgumentParser(
    description="""Binance Alper's trading bot helper""",
    epilog="""To run: nohup python3 -u ./binance_track.py > cmd.log &!""",
)


def my_bool(s):
    return s != "False"


parser.add_argument("-trade", "--trade", default=False, type=my_bool, help="FOO!")
parser.add_argument("-log", "--log", type=bool, default=False, help="FOO!")
parser.add_argument("-lag", "--lag", type=bool, default=0, help="FOO!")
args = parser.parse_args()

is_trade = vars(args)["trade"]
is_log = vars(args)["log"]
lag_time = vars(args)["lag"]


def transfer_futures_to_spot(amount):
    client.futures_account_transfer(asset="USDT", amount=float(amount), type="2")


def transfer_spot_to_futures(amount):
    client.futures_account_transfer(asset="USDT", amount=float(amount), type="1")


def transfer_spot_to_margin(amount):
    client.transfer_spot_to_margin(asset="USDT", amount=float(amount), type="1")


def get_balance_margin_USDT():
    try:
        _len = len(client.get_margin_account()["userAssets"])
        for x in range(_len):
            if client.get_margin_account()["userAssets"][x]["asset"] == "USDT":
                balance_USDT = client.get_margin_account()["userAssets"][x]["free"]
                return float(balance_USDT)
    except:
        pass

    return 0


def _format(value, decimal=2):
    return format(float(value), "." + str(decimal) + "f")


def _trade_cont(seperate_line_line, funding_dict, daily_progress, latest_symbol_income):
    seperate_line_line = True
    _symbol = None
    futures_usd = client_helper.get_futures_usdt(is_both=False)
    margin_usdt = get_balance_margin_USDT()
    total_balance = float(futures_usd) + float(usdt_balance) + margin_usdt
    log(f"==> Futures={futures_usd} USD | SPOT={_format(usdt_balance)} USD | MARGIN={margin_usdt} ", end="")
    log(f"TOTAL={_format(total_balance)}", "green")
    if float(futures_usd) > FUTURE_AMOUNT_TO_TRADE:
        try:
            amount = float(futures_usd) - FUTURE_AMOUNT_TO_TRADE
            transfer_futures_to_spot(amount)
            log(f"==> Transfered {_format(amount)} from futures to spot")
        except:
            pass

    objs = client.futures_position_information(limit=100)
    for future in objs:
        amount = future["positionAmt"]
        if float(amount) != 0.0:
            _symbol = future["symbol"]  # in order to retreive active position
            break

    # if float(total_balance) > FUTURE_AMOUNT_TO_TRADE:
    #     try:
    #         amount = float(total_balance) - FUTURE_AMOUNT_TO_TRADE
    #         transfer_spot_to_margin(amount)
    #         log(f"==> Transfered {_format(amount)} from spot to margin")
    #     except:
    #         transfer_futures_to_spot(amount)
    #         log(f"==> Transfered {_format(amount)} from futures to spot")
    #         try:
    #             transfer_spot_to_margin(amount - 0.01)
    #             log(f"==> Transfered {_format(amount)} from spot to margin")
    #         except:
    #             pass

    log("\nFunding Fee:", "cyan")
    current_date = date.today()
    for key, value in funding_dict.items():
        fund_fee = value[0]
        if fund_fee < 0.0:
            _color = "red"
        else:
            _color = "green"

        log(f"{key} => {value}", _color)
        if str(current_date) == value[1].split(" ")[0]:
            daily_progress += fund_fee

    if daily_progress < 0:
        log(f"\ndp={daily_progress}", "red")
    else:
        log(f"\ndp={daily_progress}", "green")

    if not is_log:
        enable_print()

    if not _symbol:
        pass

    if not is_trade:
        sys.exit(1)

    while True:
        if not positions(client, latest_symbol_income, daily_progress, _symbol):
            if seperate_line_line:
                log(SEP, "cyan")
                if futures_usd != 0 and float(futures_usd) > FUTURE_AMOUNT_TO_TRADE:
                    try:
                        transfer_futures_to_spot(float(futures_usd) - FUTURE_AMOUNT_TO_TRADE)
                        time.sleep(0.25)
                    except Exception as e:
                        log(f"futures=>spot {e}", "red")

                    try:
                        # transfer_spot_to_futures(FUTURE_AMOUNT_TO_TRADE)
                        # time.sleep(0.25)
                        futures_usd = client_helper.get_futures_usdt(is_both=False)
                        log(f"==> Futures={futures_usd} USD")
                    except Exception as e:
                        log(f"sport=>futures {e}", "red")

                # TODO: get balance before and after the trade to see the gain
                seperate_line_line = False
                binance_lib.START_POSITION = False
            else:
                pass
                # # TODO: here when there is no position, update with new positon if opened
                # time.sleep(0.25)
                # futures_usd = get_futures_usdt(is_both=False)
                # if futures_usd != 0 and float(futures_usd) > FUTURE_AMOUNT_TO_TRADE:
                #     transfer_futures_to_spot(float(futures_usd) - FUTURE_AMOUNT_TO_TRADE)
        else:
            seperate_line_line = True

        if lag_time > 0:
            time.sleep(lag_time * 60)
        else:
            time.sleep(0.25)


def _trade(binance, usdt_balance, is_trade=True):
    if not is_log:
        block_print()

    com, latest_symbol_income, daily_progress, funding_dict = futures_history(binance)
    # _trade_cont(funding_dict, daily_progress, latest_symbol_income)


def block_print():
    """Disable print out."""
    sys.stdout = open(os.devnull, "w")


def enable_print():
    """Resorte print out."""
    sys.stdout = sys.__stdout__


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


def telegram_msg(text, _receipt=""):
    global start
    global msg
    text = str(text)
    end = time.time()
    if end - start > 30:
        if start > 0:
            print("## Attempting to send telegram message")
        if msg:
            _mail = "\n".join(msg)
            _mail = f"{text}\nbinance_symbols@{found_ones}\n{_mail}"
            msg_to_send = f"{_mail}\n=====================================\n{_receipt}"
            start = time.time()
        else:
            msg_to_send = str(text)

        try:
            run([f"{HOME}/venv/bin/telegram-send", msg_to_send])
        except:
            log(msg_to_send)  # experimental


def find_between(string, start=r"\(", end=r"\)"):
    try:
        _lst = []
        lst = re.findall(start + r"(.*?)" + end, string)
        if lst:
            if "List" in string:
                _lst.append(lst[0])
                msg.append(string)

        for one in _lst:
            found_ones.append(one) if one not in found_ones else found_ones
    except:
        pass


def save_obj(name, syms=None):
    _file = f".{name}.pk"
    if syms is None:
        syms = {}
        _balances = balances["balances"]
        for balance in _balances:
            syms[balance["asset"]] = True

    with open(_file, "wb") as f:
        pickle.dump(syms, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    _file = f".{name}.pk"
    with open(_file, "rb") as f:
        return pickle.load(f)


def get_url(url):
    # response = urlopen(url).read()
    # download the homepage
    _response = requests.get(url, headers=headers)
    soup = BeautifulSoup(_response.text, "lxml")
    announcements = soup.find_all("a", {"class": "css-1neg3js"})
    print(announcements)


def check_url(url):
    # response = urlopen(url).read()
    # download the homepage
    _response = requests.get(url, headers=headers)
    soup = BeautifulSoup(_response.text, "lxml")
    announcements = soup.find_all("a", {"class": "css-1neg3js"})
    for ann in announcements:
        announcement = ann.text.strip()
        find_between(announcement)


def _run():
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
                        telegram_msg("found_symbol=" + _symbol)

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
                        telegram_msg(str(f_ones), "ALERT")
                        time.sleep(TIME_TO_FORCE_BUY)
            except:
                pass

            print(f"found:{found} ==> {output}")
            f_ones.append(found)

    if flag:
        while True:
            try:
                telegram_msg(str(f_ones), _receipt)
            except:
                pass
            time.sleep(60)


def trade_cont(client, balances):
    global msg
    print(client.get_asset_balance(asset=MAIN_ASSET))
    # free_asset = get_free_balance()
    # info = client.get_account()
    # margin ===============================================
    # print(client.get_open_margin_orders(symbol='ETHBTC'))
    # for d in client.get_margin_account()['userAssets']:
    #     if d['free'] != "0":
    #         print(d)

    # ua = {d['asset']: d for d in data['userAssets']}
    # print(ua['BTC']['free'])
    # ======================================================
    sum_btc = 0.0
    for _balance in balances["balances"]:
        asset = _balance["asset"]
        if float(_balance["free"]) != 0.0 and asset not in ignore_balance_list:
            try:
                if asset == "BTC":
                    sum_btc += float(_balance["free"])
                else:
                    _price = client.get_symbol_ticker(symbol=asset + "BTC")
                    sum_btc += float(_balance["free"]) * float(_price["price"])
            except:
                pass

    current_btc_price_USD = client.get_symbol_ticker(symbol="BTCUSDT")["price"]
    # current_btc_price_TRY = client.get_symbol_ticker(symbol="BTCTRY")["price"]
    # current_btc_price = client.get_symbol_ticker(symbol="BTCUSDT")["price"]
    futures_usd = client_helper.get_futures_usdt()
    log(f"==> Futures={futures_usd} USD")
    own_usd = 0.0
    own_usd = sum_btc * float(current_btc_price_USD)
    # own_try = sum_btc * float(current_btc_price_TRY)
    print("Spot => %.8f BTC == " % sum_btc, end="")
    print("%.8f USD == " % own_usd)
    print("overview => %.2f USD" % (float(own_usd) + float(futures_usd)))
    # for asset in client.futures_account_balance():
    #     name = asset["asset"]
    #     balance = asset["balance"]
    #
    # save_obj("symbols")
    # sys.exit()
    try:
        global org_symbols
        org_symbols = load_obj("symbols")
    except:
        save_obj("symbols")

    _date = datetime.now().strftime("%I:%M%p %B %d %Y")
    telegram_msg(f"==> Started ... {_date}")
    while True:
        _run()
        _date = datetime.now().strftime("%I:%M%p %B %d %Y")
        print(_date)
        msg = []
        time.sleep(SLEEP_DURATION)


if __name__ == "__main__":
    binance = Python_Binance()
    # client.futures_account_balance()[1]["withdrawAvailable"]
    for balance in binance.balances["balances"]:
        if balance["asset"] == "USDT":
            usdt_balance = balance["free"]
            break

    _trade(binance, usdt_balance, is_trade)
    # trade_cont(client, balances)

# try:
#     details = client.get_max_margin_transfer(asset="BTC")
#     print(client.get_all_margin_orders())
#     print(details)
#     # print(client.futures_account_balance())
# except:
#     pass
