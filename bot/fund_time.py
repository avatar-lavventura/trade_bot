#!/usr/bin/env python3

from datetime import datetime

import ccxt


class Fund:
    def __init__(self) -> None:
        self.midnight = None
        self.fund_times = ["00:00:00+00:00", "09:00:00+00:00", "16:00:00+00:00"]
        self.fund_times_ts = []
        self.init()
        self.fund_prices = {}
        self.binance = ccxt.binance()

    def init(self):
        now = datetime.utcnow()
        self.base_durations_ts = []
        for d in self.fund_times:
            ts = int(datetime.strptime(f"{now.strftime('%Y-%m-%d')} {d}", "%Y-%m-%d %H:%M:%S%z").timestamp() * 1000)
            if d == "00:00:00+00:00":
                self.midnight = ts

            self.fund_times_ts.append(ts)

        return now

    def percent_change_since_day_start(self, symbol):
        now = datetime.utcnow()
        times_ts = int(
            datetime.strptime(f"{now.strftime('%Y-%m-%d')} 00:00:00+00:00", "%Y-%m-%d %H:%M:%S%z").timestamp() * 1000
        )
        if (symbol, times_ts) not in self.fund_prices:
            self.fund_prices[(symbol, times_ts)] = self.binance.fetch_ohlcv(
                symbol=symbol, timeframe="1h", since=times_ts, limit=1
            )

        return self.fund_prices[(symbol, times_ts)]

    def percent_change_since_last_fund(self, symbol):
        now = self.init()
        # now = datetime.utcnow()
        _since = 0
        for times_ts in self.fund_times_ts:
            if int(now.timestamp() * 1000) > int(times_ts):
                _since = times_ts
            else:
                break
        _since = times_ts
        if (symbol, times_ts) not in self.fund_prices:
            self.fund_prices[(symbol, times_ts)] = self.binance.fetch_ohlcv(
                symbol=symbol, timeframe="1h", since=_since, limit=1
            )

        return self.fund_prices[(symbol, times_ts)]
