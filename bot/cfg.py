#!/usr/bin/env python3

from broker._utils.tools import _date

STABLE_COINS = ["USDT", "BUSD", "TUSD", "USDC", "USDP", "BNB", "ETH", "PAXG"]
SLEEP_INTERVAL: int = 20  # seconds to sleep for next balance check
discord_message: str = f"`{_date(_type='hour')}`\n"
discord_message_full: str = f"{_date(_type='hour')}\n"
discord_print: bool = False
locked_balance: float = 0.0
discord_sent_msg = None
BTCUSDT_PRICE: float = 0.0
BNB_QTY: float = 0.0
BNB_BALANCE: float = 0.0
TYPE: str = ""
BALANCES = None
SUM_BTC = None
CURRENT_DATE = None

"""
* IGNORE_SOLD_QUANTITY

Sold quantity affects the average price make it smaller showing your are in
gain, which may cause to update your sell limit order in much small price,
causing to sell right away.  // kar yaptiysan 20%'sini satip maliyetini dusuyuor
genel kar gostergesi bir anda artiyor onceki kari dikkate aldigi icin

- 8.79 de 400$ alim gerceklesti, 100$ kara satisi oldu, maliyet 8.75 olarak
guncellendi.  0.50% kar gozukurken maliyet dustugu icin o anki fiyatta kar
gostergesi 1.0% oldu, daha ucuza satis emri verme durumu olabilir emirler guncellenirse
"""
IGNORE_SOLD_QUANTITY = True  # True for all by default
_IGNORE_SOLD_QUANTITY = {}
_IGNORE_SOLD_QUANTITY["PNT/USDT"] = False
_IGNORE_SOLD_QUANTITY["ORN/USDT"] = False
