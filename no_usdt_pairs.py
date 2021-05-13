#!/usr/bin/env python3

from pathlib import Path

import requests
from binance.client import Client

HOME = str(Path.home())
client = None


if __name__ == "__main__":  # noqa: C901
    client, _ = check_binance_obj()
    balances = client.get_account()
    for _balance in balances["balances"]:
        asset = _balance["asset"]
        try:
            _price = client.get_symbol_ticker(symbol=f"{asset}USDT")
            _price = client.get_symbol_ticker(symbol=f"{asset}BUSD")
        except:
            flag = False
            try:
                _price = client.get_symbol_ticker(symbol=f"{asset}BTC")
                if not flag and asset != "USDT":
                    print(f"{asset} =>", end="")
                    flag = True
                print(" BTC ", end="")
            except:
                pass

            try:
                _price = client.get_symbol_ticker(symbol=f"{asset}BNB")
                if not flag and asset != "USDT":
                    print(f"{asset} =>", end="")
                    flag = True

                print(" BNB ", end="")
            except:
                pass

            try:
                _price = client.get_symbol_ticker(symbol=f"{asset}ETH")
                if not flag and asset != "USDT":
                    print(f"{asset} =>", end="")
                    flag = True

                print(" ETH ", end="")
            except:
                pass

            if flag:
                print("")
