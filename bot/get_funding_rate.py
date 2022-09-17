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
    ts = None
    funding = {}
    response = exchange.fetchFundingRates()
    for symbol in response:
        funding_rate = response[symbol]["info"]["lastFundingRate"]
        if abs(float(funding_rate)) > 0.007:
            info = response[symbol]["info"]
            if not ts:
                ts = info["time"]

            del info["symbol"]
            del info["interestRate"]
            del info["nextFundingTime"]
            del info["time"]

            info["markPrice"] = float(info["markPrice"])
            info["indexPrice"] = float(info["indexPrice"])
            info["estimatedSettlePrice"] = float(info["estimatedSettlePrice"])
            funding[symbol] = info
            funding_rate = float(funding[symbol]["lastFundingRate"]) * 100
            funding[symbol]["lastFundingRate"] = float(format(funding_rate, ".8f"))

    if funding:
        log(f"[b]ts={ts}", is_write=False)
        log(funding, is_write=False)
    else:
        log("#> [white]no funding rate > 0.75%", is_write=False)


def main():
    peak_funding_rates()


if __name__ == "__main__":
    main()
