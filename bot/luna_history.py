#!/usr/bin/env python3

import ccxt

exchange = ccxt.binance()


def table(values):
    first = values[0]
    keys = list(first.keys()) if isinstance(first, dict) else range(0, len(first))
    widths = [max([len(str(v[k])) for v in values]) for k in keys]
    string = " | ".join(["{:<" + str(w) + "}" for w in widths])
    return "\n".join([string.format(*[str(v[k]) for k in keys]) for v in values])


def main():
    markets = exchange.load_markets()
    symbol = "LUNA/BTC"
    since = exchange.parse8601("2022-05-01T00:00:00Z")
    ohlcvs = exchange.fetch_ohlcv(symbol, "1h", since)
    print(table([[exchange.iso8601(int(o[0]))] + o[1:] for o in ohlcvs]))


if __name__ == "__main__":
    main()
