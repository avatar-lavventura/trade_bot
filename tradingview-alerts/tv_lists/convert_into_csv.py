#!/usr/bin/env python3

# TODO: apply blacklist

is_futures = False
if is_futures:
    filename = "binance_usdt_futures.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()
            print(f"{_line},{_line.replace('USDTPERP', '').replace('BINANCE:', '')},USDTPERP,")
else:
    filename = "binance_usdt_markets.txt"
    with open(filename) as f:
        for line in f:
            _line = line.rstrip()
            print(f"{_line},{_line.replace('USDT', '').replace('BINANCE:', '')},USDT,")

    # with open(filename) as f:
    #     for line in f:
    #         _line = line.rstrip()

    # results = [x.strip() for x in _line.split(",")]
    # for res in results:
    #     _res = res.rstrip()
    #     print(f"{_res},{_res.replace('BTC', '').replace('BINANCE:', '')},BTC,")
