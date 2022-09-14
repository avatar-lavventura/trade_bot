#!/usr/bin/env python3

import ccxt
from broker._utils._log import log

exchange = ccxt.binanceusdm(
    {  #: https://docs.ccxt.com/en/latest/manual.html#funding-rate
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",
        },
    }
)


def peak_funding_rates():
    """Print assets in futures that have funding rates at edges."""
    funding = {}
    response = exchange.fetchFundingRates()
    for symbol in response:
        funding_rate = response[symbol]["info"]["lastFundingRate"]
        if abs(float(funding_rate)) > 0.007:
            funding[symbol] = response[symbol]["info"]
            funding[symbol]["lastFundingRate"] = float(funding[symbol]["lastFundingRate"]) * 100

    if funding:
        log(funding, is_write=False)
    else:
        log("#> [white]no funding rate > 0.75%", is_write=False)


def main():
    peak_funding_rates()


if __name__ == "__main__":
    main()
