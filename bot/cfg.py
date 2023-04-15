#!/usr/bin/env python3

import gspread
from broker._utils.tools import _date

from bot.sheets_lib import fetch_withdrawn

STABLE_COINS = ["USDT", "BUSD", "TUSD", "USDC", "USDP", "BNB", "ETH", "PAXG", "TRY"]
ignore_list = ["info", "BTC", "BNB", "USDT", "timestamp", "datetime", "free", "used", "total"]
SLEEP_INTERVAL: int = 20  # seconds to sleep for next balance check
discord_message_full = discord_message = f"`{_date()}`\n"
discord_print: bool = False
locked_balance: float = 0
discord_sent_msg = None
BNB_QTY: float = 0
BNB_BALANCE: float = 0
TYPE: str = ""
BALANCES = None
CURRENT_DATE = None  # zone is UTC
MINIMUM_POSITION = {}
MINIMUM_POSITION["btc"] = 0.0001
MINIMUM_POSITION["usdt"] = 10

PRICES = {}  # last price for the assets
PRICES["BTCUSDT"] = 0.0
BNBUSDT: float = 0.0  # constant set its price only at startup

ENTRY_PRICE_VERBOSE = False

# TODO: {ts, asset, price} @ mongoDB
# do not fetch price within 20 seconds for BTCUSDT

SUM_BTC: float = 0.0
BALANCE_FLAG = False
MARGIN_BAL_BTC = 0
MARGIN_BAL = 0
FIRST_PRINT_CYCLE = True

gc = gspread.service_account()
sh = gc.open("guncel_kendime_olan_borclar")

WITHDRAWN = fetch_withdrawn(sh, "usdt")
WITHDRAWN_BTC = fetch_withdrawn(sh, "btc")

order_del_list = [
    "timeInForce",
    "orderListId",
    "price",
    "status",
    "type",
    "origQty",
    "executedQty",
    "clientOrderId",
    "orderId",
    "side",
    "selfTradePreventionMode",
    "workingTime",
]

"""
* IGNORE_SOLD_QUANTITY

Sold quantity affects the average price make it smaller showing your are in
gain, which may cause to update your sell limit order in much small price,
causing to sell right away.  // kar yaptiysan 20%'sini satip maliyetini dusuyuor
genel kar gostergesi bir anda artiyor onceki kari dikkate aldigi icin

- 8.79 de 400$ alim gerceklesti, 100$ kara satisi oldu, maliyet 8.75 olarak
  guncellendi.  0.50% kar gozukurken maliyet dustugu icin o anki fiyatta kar
  gostergesi 1.0% oldu, daha ucuza satis emri verme durumu olabilir emirler
  guncellenirse
"""
IGNORE_SOLD_QUANTITY = True  # by default True for all
_IGNORE_SOLD_QUANTITY = {}
# for symbol in ["PNT/USDT", "ORN/USDT"]:
#     _IGNORE_SOLD_QUANTITY[symbol] = False
