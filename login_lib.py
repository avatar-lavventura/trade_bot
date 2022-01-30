#!/usr/bin/env python3

import os
import pickle
from pathlib import Path

from binance.client import Client

from ebloc_broker.broker._utils.yaml import Yaml

HOME = str(Path.home())


def save_obj(name, client, syms=None):
    balances = client.get_account()
    _file = f".{name}.pk"
    if syms is None:
        syms = {}
        _balances = balances["balances"]
        for balance in _balances:
            syms[balance["asset"]] = True

    with open(_file, "wb") as f:
        pickle.dump(syms, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    _file = f".{name}.pk"
    if not os.path.exists(_file):
        with open(_file, "w"):
            pass

    with open(_file, "rb") as f:
        return pickle.load(f)


def check_binance_obj():
    client = None
    try:
        client = load_obj("binance")
    except:
        HOME = Path.home()
        _cfg = Yaml(HOME / ".binance.yaml")
        api_key = str(_cfg["b"]["key"])
        api_secret = str(_cfg["b"]["secret"])
        client = Client(api_key, api_secret)
        save_obj("binance", client)

    return client
