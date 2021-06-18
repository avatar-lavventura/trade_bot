#!/usr/bin/env python3

is_futures = False
if is_futures:
    filename = "binancefutures_perpetual_futures.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()
            print(f"{_line},{_line.replace('USDTPERP', '').replace('BINANCE:', '')},USDTPERP,")
else:
    filename = "../binance_btc_markets.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()

    results = [x.strip() for x in _line.split(",")]
    for res in results:
        _res = res.rstrip()
        print(f"{_res},{_res.replace('BTC', '').replace('BINANCE:', '')},BTC,")
