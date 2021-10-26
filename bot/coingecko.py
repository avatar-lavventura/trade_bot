#!/usr/bin/env python3

import json
import subprocess

import requests


"""
currency='OOKI'
curl -X 'GET' \
  'https://api.coingecko.com/api/v3/simple/price?ids='$currency'&vs_currencies=btc' \
  -H 'accept: application/json'

__ https://www.coingecko.com/en/api/documentation?
"""


def get_coingecko_api(_id, _type="btc") -> float:
    cmd = [
        "curl",
        "-sX",
        "GET",
        f"https://api.coingecko.com/api/v3/simple/price?ids={_id}&vs_currencies=btc",
        "-H",
        "accept: application/json",
    ]
    obj = json.loads(subprocess.check_output(cmd))
    asst_in_btc = float(obj[_id]["btc"])
    if _type == "btc":
        return asst_in_btc
    elif _type == "usdt":
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        data = response.json()
        btc_price = float(data["bpi"]["USD"]["rate"].split(".")[0].replace(",", ""))
        return btc_price * asst_in_btc

    return 0.0


if __name__ == "__main__":
    currency_id = "ooki"
    asset_usdt_price = get_coingecko_api(currency_id, "usdt")
    print(asset_usdt_price)
