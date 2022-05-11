#!/usr/bin/env python3

import calendar
from datetime import datetime

import ccxt
import pandas as pd
from broker._utils._log import log


def main():
    # https://techflare.blog/how-to-get-ohlcv-data-for-your-exchange-with-ccxt-library/
    binance = ccxt.binance()

    now = datetime.utcnow()
    unixtime = calendar.timegm(now.utctimetuple())
    since = (unixtime - 60 * 60) * 1000  # UTC timestamp in milliseconds
    # timestamp = int(datetime.datetime.strptime("2018-01-24 11:20:00+00:00", "%Y-%m-%d %H:%M:%S%z").timestamp() * 1000)

    # symbol = "BTC/USDT"
    symbol = "IOTA/BTC"
    ohlcv = binance.fetch_ohlcv(symbol=symbol, timeframe="5m", since=since, limit=12)
    start_dt = datetime.fromtimestamp(ohlcv[0][0] / 1000)
    end_dt = datetime.fromtimestamp(ohlcv[-1][0] / 1000)

    # convert it into Pandas DataFrame
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)

    df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
    df.set_index("Time", inplace=True)
    print(df)
    log(ohlcv)


if __name__ == "__main__":
    main()
