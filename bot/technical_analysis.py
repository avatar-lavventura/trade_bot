#!/usr/bin/env python3

from tradingview_ta import Interval, TA_Handler

"""Python API wrapper to retrieve technical analysis from TradingView."""


def main():
    # https://python-tradingview-ta.readthedocs.io/en/latest/usage.html#retrieving-the-analysis
    tesla = TA_Handler(
        symbol="TSLA",
        screener="america",
        exchange="NASDAQ",
        interval=Interval.INTERVAL_5_MINUTES,
        # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
    )
    # tesla.get_analysis().indicators
    print(tesla.get_analysis())
    # Example output: {"RECOMMENDATION": "BUY", "BUY": 8, "NEUTRAL": 6, "SELL": 3}


if __name__ == "__main__":
    main()
