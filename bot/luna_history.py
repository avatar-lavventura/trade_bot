#!/usr/bin/env python3

import ccxt
from broker._utils._log import log

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
exchange.load_markets()


def table(values):
    first = values[0]
    keys = list(first.keys()) if isinstance(first, dict) else range(0, len(first))
    widths = [max([len(str(v[k])) for v in values]) for k in keys]
    string = " | ".join(["{:<" + str(w) + "}" for w in widths])
    return "\n".join([string.format(*[str(v[k]) for k in keys]) for v in values])


def luna_history():
    symbol = "LUNA/BTC"
    since = exchange.parse8601("2022-05-01T00:00:00Z")
    ohlcvs = exchange.fetch_ohlcv(symbol, "1h", since, limit=1500)
    print(table([[exchange.iso8601(int(o[0]))] + o[1:] for o in ohlcvs]))


def main():
    symbol = "BOND/BTC"
    order_history = exchange.fetch_trades(symbol)  # public
    cost = 0
    for item in order_history:
        # 2.54 worth of BTC 50k dumped in 1 second
        # if item["datetime"] == "2023-06-13T09:25:43.311Z":
        del item["order"]
        del item["type"]
        del item["fee"]
        del item["takerOrMaker"]
        del item["fees"]
        log(item)
        # cost += float(item["cost"])

    print(cost)


if __name__ == "__main__":
    main()
