#!/usr/bin/env python3

from datetime import datetime
from email.utils import parsedate
from pathlib import Path

import ccxt.async_support as ccxt

from bot import cfg
from ebloc_broker.broker._utils.tools import unix_time_millis
from ebloc_broker.broker._utils.yaml import Yaml

is_start = True
is_futures = False


class Exchange:
    def __init__(self):
        self.helper_cfg = None
        self.future = None
        self.spot = None
        self.spot_usdt = None
        self.spot_btc = None
        self.spot_markets = {}
        self.future_markets = {}
        self._type: str = ""

    def init_both(self):
        helper_cfg = Yaml(Path.home() / ".binance.yaml")
        ops = {
            "apiKey": str(helper_cfg["b"]["key"]),
            "secret": str(helper_cfg["b"]["secret"]),
            "options": {"adustForTimeDifference": True},
        }
        if not ops["apiKey"] or not ops["secret"]:
            raise Exception("apiKey or secret is {}")

        self.spot_usdt = ccxt.binance(ops)
        #
        ops = {
            "apiKey": str(helper_cfg["anne_b"]["key"]),
            "secret": str(helper_cfg["anne_b"]["secret"]),
            "options": {"adustForTimeDifference": True},
        }
        if not ops["apiKey"] or not ops["secret"]:
            raise Exception("apiKey or secret is {}")

        self.spot_btc = ccxt.binance(ops)
        ops = None
        helper_cfg = None

    def init(self, _type):
        self._type = _type
        helper_cfg = Yaml(Path.home() / ".binance.yaml")
        if cfg.TYPE == "usdt":
            ops = {
                "apiKey": str(helper_cfg["b"]["key"]),
                "secret": str(helper_cfg["b"]["secret"]),
                "options": {"adustForTimeDifference": True},
            }
        elif cfg.TYPE == "btc":
            ops = {
                "apiKey": str(helper_cfg["anne_b"]["key"]),
                "secret": str(helper_cfg["anne_b"]["secret"]),
                "options": {"adustForTimeDifference": True},
            }

        if not ops["apiKey"] or not ops["secret"]:
            raise Exception("apiKey or secret is {}")

        if is_futures:
            self.future = ccxt.binanceusdm(ops)

        self.spot = ccxt.binance(ops)
        ops = None
        helper_cfg = None

    def get_spot_timestamp(self):
        parsed_date = parsedate(self.spot.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_timestamp_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_timestamp_ms

    def get_future_timestamp(self):
        parsed_date = parsedate(self.future.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_timestamp_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_timestamp_ms

    async def set_markets(self):
        if self.spot_usdt:
            self.spot_markets = await self.spot_usdt.load_markets()
        else:
            self.spot_markets = await self.spot.load_markets()

        if is_futures:
            self.future_markets = await self.future.load_markets()

    async def close(self):
        await self.spot.close()
        if is_futures:
            await self.future.close()


exchange = Exchange()
