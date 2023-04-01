#!/usr/bin/env python3

from datetime import datetime

import ccxt
import pandas as pd
from broker._utils.tools import print_tb

binance = ccxt.binanceusdm({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
binanceusdm = ccxt.binanceusdm({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})


def fetch_ohlcv():
    symbol = "LUNAUSDT"
    ohlcv = binance.fetch_ohlcv(symbol, "1d")
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
    df.set_index("Time", inplace=True)
    print(df)


def fetch_ohlcv_perp():
    ohlcv = binanceusdm.fetch_ohlcv("ICP/USDT", "5m", limit=1000)
    # print(ohlcv)
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
    df.set_index("Time", inplace=True)
    print(df)


def main():
    # fetcch_ohlcv()
    try:
        fetch_ohlcv_perp()
    except Exception as e:
        print_tb(e)


if __name__ == "__main__":
    main()
