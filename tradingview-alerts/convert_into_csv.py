#!/usr/bin/env python3

is_futures = True
if is_futures:
    filename = "tv_lists/binance_usdt_futures.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()
            print(f"{_line},{_line.replace('USDTPERP', '').replace('BINANCE:', '')},USDTPERP,")
else:
    filename = "tv_list/binance_spot.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()

    results = [x.strip() for x in _line.split(",")]
    for res in results:
        _res = res.rstrip()
        print(f"{_res},{_res.replace('BTC', '').replace('BINANCE:', '')},BTC,")
