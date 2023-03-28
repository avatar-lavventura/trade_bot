#!/usr/bin/env python3

# https://github.com/man-c/pycoingecko

from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()
price = cg.get_price(ids="cocos-bcx", vs_currencies="btc")
print(price["cocos-bcx"]["btc"])

price = cg.get_price(ids="binancecoin", vs_currencies="usd")
print(price["binancecoin"]["usd"])
