#!/usr/bin/env python3

import calendar
import re
from datetime import datetime

import ccxt
import pandas as pd
from broker._utils._log import log

from bot import cfg
from bot.fund_time import Fund

# https://techflare.blog/how-to-get-ohlcv-data-for-your-exchange-with-ccxt-library/

fund = Fund()

binance = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
# def percent_change_since_fund(symbol):
#     now = datetime.utcnow()
#     _since = 0
#     for times_ts in fund.fund_times_ts:
#         if int(now.timestamp() * 1000) > int(times_ts):
#             _since = times_ts
#         else:
#             break

#     if (symbol, times_ts) not in fund_prices:
#         fund_prices[(symbol, times_ts)] = binance.fetch_ohlcv(symbol=symbol, timeframe="1h", since=_since, limit=1)

#     return fund_prices[(symbol, times_ts)]


def one_hr(symbol, _since=60):
    now = datetime.utcnow()
    unixtime = calendar.timegm(now.utctimetuple())
    since = (unixtime - _since * _since) * 1000  # UTC timestamp in milliseconds
    ohlcv = binance.fetch_ohlcv(symbol=symbol, timeframe="5m", since=since, limit=12)
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
    df.set_index("Time", inplace=True)
    log(ohlcv)


def _fetch_ohlcv(ohlcv, symbol, is_compact=False):
    if is_compact:
        _ohl = ohlcv[0][1:-2] + ["{:,.0f}".format(ohlcv[0][-1])]
        if float(_ohl[0]) > 10000:  # for btc
            for i in range(0, 4):
                if i != 3:
                    _ohl[i] = int(_ohl[i])
        elif float(_ohl[0]) < 0.1:
            for i in range(0, 4):
                if i != 3:
                    _ohl[i] = str(_ohl[i]).lstrip("0.").lstrip("0")

        ohlcv = [_ohl]
        if symbol[-3:] == "BTC":
            pattern = r"(?m)(?<=\d)\d{3}(?=(?:\d{3})*$)"
            if float(ohlcv[0][3].replace(",", "")) >= 1000:
                ohlcv[0][3] = int(float(ohlcv[0][3].replace(",", ".").replace(".", "")) * cfg.PRICES["BTCUSDT"])
            else:
                ohlcv[0][3] = int(float(ohlcv[0][3]) / 1000 * cfg.PRICES["BTCUSDT"])

            ohlcv[0][3] = re.sub(pattern, r",\g<0>", str(ohlcv[0][3]))

    # convert it into Pandas DataFrame
    pd.set_option("display.max_columns", 1000, "display.width", 1000, "display.max_rows", 1000)
    if is_compact:
        df = pd.DataFrame(ohlcv, columns=["Open", "High", "Low", "Volume"])
    else:
        df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
        df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
        df.set_index("Time", inplace=True)

    return df


def main(symbol):
    # now = datetime.utcnow()
    # _since = 0
    # print(fund.fund_times_ts)
    # for times_ts in fund.fund_times_ts:
    #     if int(now.timestamp() * 1000) > int(times_ts):
    #         _since = times_ts
    #         print(_since)
    #     else:
    #         break

    # _since = fund.midnight
    ohlcv = binance.fetch_ohlcv(symbol=symbol, timeframe="4h", limit=24)
    df = _fetch_ohlcv(ohlcv, symbol)

    ohlcv = binance.fetch_ohlcv(symbol=symbol, timeframe="1h", limit=1)
    df = _fetch_ohlcv(ohlcv, symbol, is_compact=True)

    ohlcv = binance.fetch_ohlcv(symbol=symbol, timeframe="1d", limit=1)
    df = _fetch_ohlcv(ohlcv, symbol, is_compact=True)

    print(df)
    print()


if __name__ == "__main__":
    # symbol = "JOEUSDT"
    symbol = "BTCUSDT"
    main(symbol)
    # symbol = "FTMUSDT"
    # output = fund.percent_change_since_fund(symbol)
    # print(output)
    # output = percent_change_since_fund(symbol)
    # print(output)
    # output = percent_change_since_fund(symbol)
    # print(output)
    # one_hr("LUNAUSDT", _since=600)
