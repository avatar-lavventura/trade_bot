#!/usr/bin/env python3

import calendar
from datetime import datetime

import ccxt
import pandas as pd
from broker._utils._log import log

from bot.fund_time import Fund

binance = ccxt.binance()

symbol = "LUNAUSDT"
ohlcv = binance.fetch_ohlcv(symbol, "1d")
pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
df.set_index("Time", inplace=True)
print(df)
