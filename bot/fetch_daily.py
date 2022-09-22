#!/usr/bin/env python3

from datetime import datetime

import ccxt
import pandas as pd

binance = ccxt.binance()


def fetch_ohlcv():
    symbol = "LUNAUSDT"
    ohlcv = binance.fetch_ohlcv(symbol, "1d")
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
    df.set_index("Time", inplace=True)
    print(df)


def main():
    fetch_ohlcv()


if __name__ == "__main__":
    main()
