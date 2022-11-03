#!/usr/bin/env python3

from contextlib import suppress
from datetime import datetime
from email.utils import parsedate
from pathlib import Path

import ccxt.async_support as ccxt
from broker._utils.tools import unix_time_millis
from broker._utils.yaml import Yaml

from bot import cfg
from bot.config import config

is_start = True


class Exchange:
    def __init__(self):
        self.spot = None
        self.spot_usdt = None
        self.spot_btc = None
        self.margin = None
        self.spot_markets = {}
        self._type: str = ""

    def init_both(self):
        self.spot_usdt = ccxt.binance(self.ops_check("alper_b"))
        self.spot_btc = ccxt.binance(self.ops_check("anne_b"))

    def init(self, _type):
        self._type = _type
        if cfg.TYPE == "usdt":
            ops = self.ops_check("alper_b")
            self.spot = ccxt.binance(ops)
        elif cfg.TYPE == "btc":
            ops = self.ops_check("anne_b")
            self.spot = ccxt.binance(ops)

        ops["options"] = {
            "adustForTimeDifference": True,
            "defaultMarginMode": "isolated",
        }
        self.margin = ccxt.binance(ops)

    def ops_check(self, key):
        _cfg = Yaml(Path.home() / ".binance.yaml")
        ops = {
            "apiKey": str(_cfg[key]["key"]),
            "secret": str(_cfg[key]["secret"]),
            "options": {"adustForTimeDifference": True},
        }
        _cfg = None
        if not ops["apiKey"] or not ops["secret"]:
            raise Exception("apiKey or secret is {}")

        return ops

    def get_spot_timestamp(self):
        parsed_date = parsedate(self.spot.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_ts_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_ts_ms

    async def record_balance(self):
        _balances = await self.margin.fetch_balance()
        _btc_bal = float(_balances["info"]["assets"][0]["baseAsset"]["free"])
        _usdt_bal = float(_balances["info"]["assets"][0]["quoteAsset"]["totalAsset"])
        _b = _btc_bal + _usdt_bal / cfg.PRICES["BTCUSDT"]
        _u = _btc_bal * cfg.PRICES["BTCUSDT"] + _usdt_bal
        config.env[cfg.TYPE].balance.add_single_key(
            cfg.CURRENT_DATE,
            {
                "btc": float(config.env[cfg.TYPE].balance_sum.find_one("btc")["value"]) + _b,
                "usdt": float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"]) + _u,
            },
        )

    async def set_markets(self):
        if self.spot_usdt:
            self.spot_markets = await self.spot_usdt.load_markets()
        else:
            self.spot_markets = await self.spot.load_markets()

    async def close(self):
        with suppress(Exception):
            await self.spot.close()

        with suppress(Exception):
            await self.spot_btc.close()

        with suppress(Exception):
            await self.spot_usdt.close()


exchange = Exchange()
