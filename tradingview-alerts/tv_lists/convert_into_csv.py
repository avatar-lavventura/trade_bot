#!/usr/bin/env python3

import sys

# is_futures = False
# if is_futures:
#     filename = "binance_usdt_futures.txt"
#     with open(filename) as f:
#         for line in f:
#             _line = line.rstrip()
#             print(f"{_line},{_line.replace('USDTPERP', '').replace('BINANCE:', '')},USDTPERP,")

filename = sys.argv[1]
with open(filename) as f:
    for line in f:
        _line = line.rstrip()
        print(f"{_line},{_line.replace('USDT', '').replace('BINANCE:', '')},USDT,")
