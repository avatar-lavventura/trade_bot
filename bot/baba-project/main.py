#!/usr/bin/env python3

from broker._utils._log import log
from tradingview_ta import Interval, TA_Handler


"""
https://github.com/brian-the-dev/python-tradingview-ta
https://www.tradingview.com/chart/bHXZrXAy/?symbol=BINANCE%3ACOCOSUSDT
"""


def main():
    # https://tvdb.brianthe.dev
    tesla = TA_Handler(
        symbol="YKBNK",
        screener="turkey",
        exchange="BIST",
        interval=Interval.INTERVAL_5_MINUTES,
        # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
    )
    osc = tesla.get_analysis().oscillators
    log(osc)

    if osc["COMPUTE"]["Mom"] == "SELL" and osc["COMPUTE"]["MACD"] == "SELL":
        pass


if __name__ == "__main__":
    main()
