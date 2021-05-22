#!/usr/bin/env python3

is_futures = True
if is_futures:
    filename = "binancefutures_perpetual_main.txt"
    with open(filename) as f:
        for line in f:
            line = line.rstrip()
            print(f"{line},{line.replace('USDTPERP', '').replace('BINANCE:', '')},USDTPERP,")
else:
    filename = "../binance_btc_markets.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()

    results = [x.strip() for x in _line.split(",")]
    for res in results:
        _res = res.rstrip()
        print(f"{_res},{_res.replace('BTC', '').replace('BINANCE:', '')},BTC,")
