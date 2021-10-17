#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path

import requests
from binance.client import Client

from ebloc_broker.broker._utils.yaml import Yaml

client = None
HOME = Path.home()


def save_obj(fname, client=None):
    if client is None:
        syms = {}
        balances = client.get_account()
        _balances = balances["balances"]
        for balance in _balances:
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
    save_fname = f"{HOME}/.binance.pk"
    try:
        client = load_obj(save_fname)
    except:
        _cfg = Yaml(HOME / ".binance.yaml")
        api_key = str(_cfg["b"]["key"])
        api_secret = str(_cfg["b"]["secret"])
        client = Client(api_key, api_secret)
        save_obj(save_fname, client)

    try:
        return client, client.get_account()
    except requests.exceptions.ConnectionError:
        print("ConnectionError")
        sys.exit()


if __name__ == "__main__":
    check_binance_obj()
