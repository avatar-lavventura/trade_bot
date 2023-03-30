#!/usr/bin/env python3

from datetime import datetime

from bot import cfg
from bot.config import exchange


class Fund:
    def __init__(self) -> None:
        self.midnight = None
        self.fund_times_ts = []
        self.fund_prices = {}
        self.fund_times = ["00:00:00+00:00", "09:00:00+00:00", "16:00:00+00:00"]
        self.init()
        self.binance = exchange.binance
        self.bitmex = exchange.bitmex
        self.RECORDS_BAR_1D = {}

    def init(self):
        now = datetime.utcnow()
        self.base_durations_ts = []
        for d in self.fund_times:
            ts = int(datetime.strptime(f"{now.strftime('%Y-%m-%d')} {d}", "%Y-%m-%d %H:%M:%S%z").timestamp() * 1000)
            if d == "00:00:00+00:00":
                self.midnight = ts

            self.fund_times_ts.append(ts)

        return now

    def parse_now(self, now) -> int:
        cls = f"{now.strftime('%Y-%m-%d')} 00:00:00+00:00"
        date_string = "%Y-%m-%d %H:%M:%S%z"
        return int(datetime.strptime(cls, date_string).timestamp() * 1000)

    async def _bar_ohlcv(self, symbol, tf):
        times_ts = self.parse_now(datetime.utcnow())
        if symbol == "BTCUSDT":
            _bar = await self.bitmex.fetch_ohlcv(symbol="BTC/USDT:USDT", timeframe=tf, limit=1)
            cfg.PRICES["BTCUSDT"] = _bar[0][4]
        else:
            _bar = await self.binance.fetch_ohlcv(symbol=symbol, timeframe=tf, limit=1)
        if (symbol, times_ts) not in self.fund_prices:
            self.fund_prices[(symbol, times_ts)] = _bar
            # symbol=symbol, timeframe="1d", since=times_ts, limit=1

        # TODO: check timestamp is it frozen or not >1h relative is unresponsive binance
        self.RECORDS_BAR_1D[symbol] = _bar
        return _bar

    async def percent_change_since_last_fund(self, symbol):  # TODO: check this function?
        now = self.init()
        times_ts = self.parse_now(now)
        # now = datetime.utcnow()
        _since = 0
        for times_ts in self.fund_times_ts:
            if int(now.timestamp() * 1000) > int(times_ts):
                _since = times_ts
            else:
                break

            _since = times_ts

        if (symbol, times_ts) not in self.fund_prices:
            self.fund_prices[(symbol, times_ts)] = await self.binance.fetch_ohlcv(
                symbol=symbol, timeframe="1h", since=_since, limit=1
            )

        return self.fund_prices[(symbol, times_ts)]
