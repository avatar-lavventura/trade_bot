#!/usr/bin/env python3

import ccxt

exchange = ccxt.binance()
exchange_time = exchange.public_get_time()["serverTime"]
your_time = exchange.milliseconds()
print("Exchange UTC time:", exchange_time, exchange.iso8601(exchange_time))
print("Your____ UTC time:", your_time, exchange.iso8601(your_time))
