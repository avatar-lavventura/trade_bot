#!/usr/bin/env python3

import ccxt
from broker._utils._log import log


def main():
    #  https://docs.ccxt.com/en/latest/manual.html#funding-rate
    exchange = ccxt.binanceusdm(
        {
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
            },
        }
    )
    funding = {}
    response = exchange.fetchFundingRates()
    for symbol in response:
        funding_rate = response[symbol]["info"]["lastFundingRate"]
        if abs(float(funding_rate)) > 0.0075:
            funding[symbol] = response[symbol]["info"]
            funding[symbol]["lastFundingRate"] = float(funding[symbol]["lastFundingRate"]) * 100

    log(funding, is_write=False)


if __name__ == "__main__":
    main()
