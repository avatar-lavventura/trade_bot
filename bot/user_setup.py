#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path

import requests
from binance.client import Client

HOME = str(Path.home())
client = None


def save_obj(name, client=None):
    _file = f".{name}.pk"
    if client is None:
        syms = {}
        balances = client.get_account()
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
    global client
    try:
        client = load_obj("binance")
    except:
        _file = f"{HOME}/.binance.txt"
        if not os.path.exists(_file):
            with open(_file, "w"):
                pass

        file1 = open(_file, "r")
        Lines = file1.readlines()
        api_key = str(Lines[0].strip())
        api_secret = str(Lines[1].strip())
        client = Client(api_key, api_secret)
        save_obj("binance", client)

    try:
        balances = client.get_account()
        return client, balances
    except requests.exceptions.ConnectionError:
        print("ConnectionError")
        sys.exit()
