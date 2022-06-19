#!/usr/bin/env python3

STABLE_COINS = ["USDT", "BUSD", "TUSD", "USDC", "USDP", "BNB", "ETH", "PAXG"]
SLEEP_INTERVAL: int = 30  # seconds to sleep for next balance check
discord_message: str = ".\n"
discord_message_full: str = ".\n"
discord_print: bool = False
locked_balance: float = 0.0
discord_sent_msg = None
BTCUSDT_PRICE: float = 0.0
CURRENT_DATE = None
BALANCES = None
SUM_BTC = None
BNB_QTY: float = 0.0
BNB_BALANCE: float = 0.0
TYPE: str = ""

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
IGNORE_SOLD_QUANTITY = True
_IGNORE_SOLD_QUANTITY = {}
_IGNORE_SOLD_QUANTITY["PNT/USDT"] = False
