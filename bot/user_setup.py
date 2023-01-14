#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path

import requests
from binance.client import Client
from broker._utils.yaml import Yaml

client = None
HOME = Path.home()


def save_obj(fname, client=None):
    if client is None:
        syms = {}
        balances = client.get_account()
        for balance in balances["balances"]:
            syms[balance["asset"]] = True

        with open(fname, "wb") as f:
            pickle.dump(syms, f, pickle.HIGHEST_PROTOCOL)


def load_obj(fname):
    if not os.path.exists(fname):
        with open(fname, "w"):
            pass

    with open(fname, "rb") as f:
        return pickle.load(f)


def check_binance_obj():
    global client
    save_fn = f"{HOME}/.binance.pk"
    try:
        client = load_obj(save_fn)
    except:
        k = "alper_b"
        _cfg = Yaml(HOME / ".binance.yaml")
        api_key = str(_cfg[k]["key"])
        api_secret = str(_cfg[k]["secret"])
        client = Client(api_key, api_secret)
        save_obj(save_fn, client)

    try:
        return client, client.get_account()
    except requests.exceptions.ConnectionError:
        print("E: ConnectionError")
        sys.exit()


if __name__ == "__main__":
    check_binance_obj()
