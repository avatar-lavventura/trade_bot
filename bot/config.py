#!/usr/bin/env python3

import os
import shutil
from contextlib import suppress
from datetime import datetime
from email.utils import parsedate
from pathlib import Path
from typing import Dict  # noqa: F401

import ccxt.async_support as ccxt
from broker._utils._log import log
from broker._utils.tools import unix_time_millis
from broker._utils.yaml import Yaml
from filelock import FileLock
from pycoingecko import CoinGeckoAPI
from pymongo import MongoClient

from bot import cfg
from bot.mongodb import Mongo

mc = MongoClient()


class Env:
    def __init__(self) -> None:
        self.multiply_ratio: float = 1.0
        self.percent_change_to_add = None
        self.is_manual_trade = None
        self.usdt_multiply_ratio = None
        self.positions_alert = None
        self.balance = None
        self.hit = None
        self.risk = None
        self.stats = None
        self.status = None
        self._status = None
        self._ts = None
        self.max_pos = None
        self.timestamps = None


class Exchange:
    def __init__(self) -> None:
        self.spot_markets = {}  # noqa
        self.spot = None
        self.spot_usdt = None
        self.spot_btc = None
        self.margin_isolated = None
        self.margin_cross = None
        self._type: str = ""
        args = {"options": {"adustForTimeDifference": True}, "enableRateLimit": True}
        self.binance = ccxt.binance(args)
        self.bitmex = ccxt.bitmex(args)
        self.hitbtc = ccxt.hitbtc(args)
        self.cg = CoinGeckoAPI()
        # self.mexc = ccxt.mexc(args)

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
        self.margin_isolated = ccxt.binance(ops)

        ops["options"] = {
            "adustForTimeDifference": True,
            "defaultMarginMode": "cross",
        }
        self.margin_cross = ccxt.binance(ops)

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

    def _set_bnbusdt(self):
        price = self.cg.get_price(ids="binancecoin", vs_currencies="usd")
        cfg.BNBUSDT = price["binancecoin"]["usd"]

    async def set_bnbusdt(self):
        try:
            price = self.cg.get_price(ids="binancecoin", vs_currencies="usd")
            cfg.BNBUSDT = price["binancecoin"]["usd"]
        except:
            output = await self.spot.fetch_ticker("BNBUSDT")
            cfg.BNBUSDT = output["close"]

    def get_spot_timestamp(self):
        parsed_date = parsedate(self.spot.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_ts_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_ts_ms

    async def get_cross_balance(self):
        return await self.margin_cross.fetch_balance()

    async def get_isolated_balance(self):
        return await self.margin_isolated.fetch_balance()

    def f(self, value, decimal):
        return float(format(value, f".{decimal}f"))

    async def record_balance(self):
        # await bot_async.read_margin_cross_balance()
        # binance_balance.bot_async
        margin_balance = await self.get_isolated_balance()
        _btc_bal = float(margin_balance["info"]["assets"][0]["baseAsset"]["free"])
        _usdt_bal = float(margin_balance["info"]["assets"][0]["quoteAsset"]["totalAsset"])
        btc_asset = float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"]) / cfg.PRICES["BTCUSDT"]
        _u = _btc_bal * cfg.PRICES["BTCUSDT"] + _usdt_bal
        balances_cross = await self.get_cross_balance()
        _c = float(balances_cross["info"]["totalNetAssetOfBtc"]) * cfg.PRICES["BTCUSDT"]
        usdt_asset = float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"]) + _u + _c
        if float(format(btc_asset, ".8f")) > 0.0001:
            _only_btc = float(config.env[cfg.TYPE].estimated_balance.find_one("only_btc")["value"])
            # if _only_btc > 0:
            if cfg.TYPE == "btc":
                remaining_asset_in_usdt = (
                    float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"])
                    - float(_only_btc) * cfg.PRICES["BTCUSDT"]
                )
                o_usdt = float(format(remaining_asset_in_usdt, ".2f"))
                if abs(o_usdt) == 0:
                    o_usdt = 0

                config.env[cfg.TYPE].balance.add_single_key(
                    cfg.CURRENT_DATE,
                    {
                        "BTCUSDT": int(cfg.PRICES["BTCUSDT"]),
                        "o_btc": self.f(_only_btc + cfg.TRBINANCE_BTC, 8),
                        "o_usdt": o_usdt,
                        "btc": self.f(btc_asset, 8),
                        "total": float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"]),
                        "bnb": float(format(cfg.BNB_BALANCE, ".2f")),
                    },
                )
            else:
                config.env[cfg.TYPE].balance.add_single_key(
                    cfg.CURRENT_DATE,
                    {
                        "BTCUSDT": int(cfg.PRICES["BTCUSDT"]),
                        "o_btc": _only_btc,
                        # "btc": float(format(btc_asset, ".8f")),
                        "usdt": float(format(usdt_asset, ".2f")),
                        "bnb": float(format(cfg.BNB_BALANCE, ".2f")),
                    },
                )
        else:
            config.env[cfg.TYPE].balance.add_single_key(
                cfg.CURRENT_DATE,
                {
                    "BTCUSDT": int(cfg.PRICES["BTCUSDT"]),
                    "usdt": float(format(usdt_asset, ".2f")),
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


class Config:
    def __init__(self) -> None:
        self.sum_usdt: float = 0.0
        self.base_dir = Path.home() / ".bot"
        self.initial_usdt_qty_short = {}  # type: Dict[str, int]
        self.initial_usdt_qty_long = {}  # type: Dict[str, int]
        self.btc_wavetrend = {}  # type: Dict[str, str]
        # self.locked_per_limit_usdtperp = None
        self.asset_list = []
        self.btc_quantity = {}
        self._env = None  #: shorted name
        self.env = {}  # type: Dict[str, Env]
        self.prices = {}  # type: Dict[str, Env]
        for idx in ["usdt", "btc"]:  # "busd"
            self.env[idx] = Env()  # should be initialized before reload()

        self._reload()
        self.prices = Mongo(mc, mc["shared"]["prices"])

        # self.watchlist_mb = Mongo(mc, mc["watchlist"])
        for asset in ["usdt", "btc"]:
            self.env[asset].balance = Mongo(mc, mc[asset]["balance"])
            self.env[asset].balance_sum = Mongo(mc, mc[asset]["balance"])  # # TODO: ? same as balance check
            self.env[asset].hit = Mongo(mc, mc[asset]["hit"])
            self.env[asset].stats = Mongo(mc, mc[asset]["stats"])
            self.env[asset]._status = Mongo(mc, mc[asset]["status"])
            self.env[asset]._ts = Mongo(mc, mc[asset]["timestamp"])
            self.env[asset].estimated_balance = Mongo(mc, mc[asset]["estimated_balance"])
            if not self.env[asset]._status.find_one("count"):
                self.env[asset]._status.add_single_key("count", 0)

    def total_balance(self, _type) -> float:
        try:
            return float(self.env[_type].estimated_balance.find_one("total_balance")["value"])
        except:
            return 0

    def estimated_balance(self) -> int:
        balance_brave = self.total_balance("usdt")
        balance_chrome = self.total_balance("btc")
        return int(balance_brave + balance_chrome)

    async def get_spot_timestamp(self, asset, symbol=None) -> int:
        """Returns asset's set timestamp and updates if it is not set."""
        if asset not in self.env[cfg.TYPE].timestamps["root"]:
            if not symbol:
                symbol = f"{asset}{cfg.TYPE.upper()}"

            try:
                # fetch latest recorded timestamp before program closed from mongoDB
                ts = config.env[cfg.TYPE]._ts.find_one("latest")["value"]
            except:
                ts = int(config.env[cfg.TYPE].status["timestamp"])

            if not ts:
                ts = int(config.env[cfg.TYPE].status["timestamp"])

            if len(str(ts)) == 10:
                _ts = ts * 1000

            try:
                _trades = await exchange.spot.fetch_my_trades(symbol, since=_ts)
            except Exception as e:
                if "/USDT" in symbol:
                    _trades = await exchange.spot.fetch_my_trades(symbol.replace("/USDT", "/BUSD"), since=_ts)
                else:
                    raise e

            to_set_ts = _ts
            with suppress(Exception):
                for _, trade in enumerate(_trades):
                    if cfg.ENTRY_PRICE_VERBOSE:
                        log("config.get_spot_timestamp():", is_write=False)

                    t = trade.copy()
                    for k in ["info", "fee", "fees", "takerOrMaker", "type", "id", "order", "cost", "side"]:
                        del t[k]

                    if cfg.ENTRY_PRICE_VERBOSE:
                        log(t, is_write=False)

                    if trade["info"]["isBuyer"]:
                        order_id = trade["info"]["orderId"]
                        first_orders = await exchange.spot.fetch_order_trades(order_id, symbol=symbol)
                        # at exact 20 seconds cycle large trades splitted and partially made
                        first_orders_ts = first_orders[0]["timestamp"]
                        if 0 < first_orders_ts < _ts:
                            # update few seconds behind such as ts - 9
                            to_set_ts = first_orders_ts

                        break

            self.env[cfg.TYPE].timestamps["root"][asset] = to_set_ts

        return int(self.env[cfg.TYPE].timestamps["root"][asset])

    def _yaml_wrapper(self, path, dirname, fn, auto_dump=True):
        _fn = f"initialize_{fn}.lock"
        if fn[0] == ".":
            fp_lockname = _fn
        else:
            fp_lockname = f".{_fn}"

        fp_lock = os.path.join(dirname, fp_lockname)
        with FileLock(fp_lock, timeout=5):
            yaml_obj = Yaml(path, auto_dump=auto_dump)

        if os.path.isfile(fp_lock):
            with suppress(FileNotFoundError):
                os.remove(fp_lock)

        return yaml_obj

    def yaml_wrapper(self, path, auto_dump=True):
        dirname = os.path.dirname(os.path.abspath(path))
        fn = os.path.basename(path)
        try:
            return self._yaml_wrapper(path, dirname, fn, auto_dump)
        except:
            shutil.copyfile(Path.home() / "bot" / "yaml_files" / fn, path)
            return self._yaml_wrapper(path, dirname, fn)

    def reload_wavetrend(self) -> None:
        self.btc_wavetrend = self.yaml_wrapper(self.base_dir / "btc_wavetrend.yaml")

    def _reload_cfg(self) -> None:
        self.cfg = self.yaml_wrapper(self.base_dir / "config.yaml", auto_dump=False)
        self._c = self.cfg["root"][cfg.TYPE]
        self.take_profit = float(self.cfg["root"]["take_profit"]) + 0.0001
        self.discord_msg_above_usdt = self.cfg["root"]["discord_msg_above_usdt"]
        self.isolated_wallet_limit = self.cfg["root"]["isolated_wallet_limit"]
        self.is_funding_rate_alert = self.cfg["root"]["is_funding_rate_alert"]
        for _type in ["usdt", "btc"]:  # "busd"
            self.env[_type].percent_change_to_add = -abs(self.cfg["root"][_type]["percent_change_to_add"]) + 0.01
            self.env[_type].is_manual_trade = self.cfg["root"][_type]["is_manual_trade"]
            self.env[_type].multiply_ratio = self.cfg["root"][_type]["multiply_ratio"]
            self.env[_type].positions_alert = self.yaml_wrapper(self.base_dir / f"positions_alert_{_type}.yaml")
            self.env[_type].max_pos = self.cfg["root"][_type]["max_pos"]
            self.env[_type].cross = self.cfg["root"][_type]["cross"]
            self.env[_type].isolated = self.cfg["root"][_type]["isolated"]
            self.env[_type].stop_trade_wt_30m_red = self.cfg["root"][_type]["stop_trade_wt_30m_red"]
            self.env[_type].timestamps = self.yaml_wrapper(self.base_dir / f"timestamp_{_type}.yaml")

        self.SPOT_IGNORE_LIST = self.cfg["root"]["ignore"]
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.SPOT_locked_percent_limit = self.cfg["root"]["locked_percent_limit"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["root"]["btc"]["multiply_ratio"]
        self.initial_btc_quantity = self.cfg["root"]["btc"]["initial"]

    def _reload(self) -> None:
        self._reload_cfg()
        self.alerts = self.yaml_wrapper(self.base_dir / "alerts.yaml", auto_dump=False)
        self.watchlist = self.yaml_wrapper(self.base_dir / "watchlist.yaml", auto_dump=False)
        self.reload_wavetrend()
        self.goal = self.yaml_wrapper(self.base_dir / "goal.yaml")
        self.ALERTS = self.alerts["alerts"]
        if "liquidate" in self.watchlist["watch"]:
            self.WATCHLIST_LIQUIDATE = self.watchlist["watch"]["liquidate"]

        self.WATCHLIST_TARGET = self.watchlist["watch"]["target"]
        self.WATCHLIST_BAR = self.watchlist["watch"]["bar"]
        self.WATCHLIST = self.watchlist["watch"]["list"]
        self.WATCHLIST = list(set(self.WATCHLIST + self.WATCHLIST_BAR))
        self.WATCHLIST.sort()
        self.WATCHLIST = ["BTCUSDT"] + self.WATCHLIST
        for _type in ["usdt", "btc"]:  # "busd"
            self.env[_type].status = self.yaml_wrapper(self.base_dir / f"status_{_type}.yaml")
            self.env[_type].risk = self.yaml_wrapper(self.base_dir / f"risk_{_type}.yaml")["root"]

    # BUSD
    # ====
    def get_spot_timestamp_busd(self, asset) -> int:
        if self.env[cfg.TYPE].timestamps["root"][asset] == {}:
            self.env[cfg.TYPE].timestamps["root"][asset] = config.env["busd"].status["timestamp"]

        return int(self.env[cfg.TYPE].timestamps["root"][asset])


config: Config = Config()
exchange = Exchange()
