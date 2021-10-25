#!/usr/bin/env python3

from datetime import datetime
from email.utils import parsedate
from pathlib import Path

import ccxt.async_support as ccxt
from ebloc_broker.broker._utils.tools import unix_time_millis
from ebloc_broker.broker._utils.yaml import Yaml


class Exchange:
    def __init__(self):
        helper_cfg = Yaml(Path.home() / ".binance.yaml")
        ops = {
            "apiKey": str(helper_cfg["b"]["key"]),
            "secret": str(helper_cfg["b"]["secret"]),
            "options": {"adustForTimeDifference": True},
            # "verbose": True,
        }
        if not ops["apiKey"] or not ops["secret"]:
            print("E: apiKey or secret is {}")
            breakpoint()  # DEBUG

        self.future = ccxt.binanceusdm(ops)
        self.spot = ccxt.binance(ops)
        self.future_markets = {}
        self.spot_markets = {}
        ops = None
        helper_cfg = None

    def get_future_timestamp(self):
        parsed_date = parsedate(self.future.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_timestamp_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_timestamp_ms

    async def set_markets(self):
        self.future_markets = await self.future.load_markets()
        self.spot_markets = await self.spot.load_markets()

    async def close(self):
        await self.future.close()
        await self.spot.close()


exchange = Exchange()
is_start = True
