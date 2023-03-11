#!/usr/bin/env python3

import os
import shutil
from contextlib import suppress
from datetime import datetime
from email.utils import parsedate
from pathlib import Path
from typing import Dict

import ccxt.async_support as ccxt
from broker._utils._log import log
from broker._utils.tools import unix_time_millis
from broker._utils.yaml import Yaml
from filelock import FileLock
from pymongo import MongoClient

from bot import cfg
from bot.mongodb import Mongo

mc = MongoClient()


class Env:
    def __init__(self) -> None:
        self.multiply_ratio: float = 1.0
        self.percent_change_to_add = None
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


class Exchange:
    def __init__(self) -> None:
        self.spot_markets = {}  # noqa
        self.spot = None
        self.spot_usdt = None
        self.spot_btc = None
        self.margin_isolated = None
        self.margin_cross = None
        self._type: str = ""
        self.binance = ccxt.binance()

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

    def get_spot_timestamp(self):
        parsed_date = parsedate(self.spot.last_response_headers["Date"])
        dt = datetime(*parsed_date[:6])
        unix_ts_ms = int(float(unix_time_millis(dt)) / 1000)
        return unix_ts_ms

    async def get_cross_balance(self):
        return await self.margin_cross.fetch_balance()

    async def get_isolated_balance(self):
        return await self.margin_isolated.fetch_balance()

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
            if _only_btc > 0:
                remaining_asset_in_usdt = (
                    float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"])
                    - float(_only_btc) * cfg.PRICES["BTCUSDT"]
                )
                config.env[cfg.TYPE].balance.add_single_key(
                    cfg.CURRENT_DATE,
                    {
                        "BTCUSDT": int(cfg.PRICES["BTCUSDT"]),
                        "o_btc": _only_btc,
                        "o_usdt": float(format(remaining_asset_in_usdt, ".2f")),
                        "btc": float(format(btc_asset, ".8f")),
                        "usdt": float(config.env[cfg.TYPE].balance_sum.find_one("usdt")["value"]),
                    },
                )
            else:
                config.env[cfg.TYPE].balance.add_single_key(
                    cfg.CURRENT_DATE,
                    {
                        "BTCUSDT": int(cfg.PRICES["BTCUSDT"]),
                        "btc": float(format(btc_asset, ".8f")),
                        "usdt": float(format(usdt_asset, ".2f")),
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
        self.locked_per_limit_usdtperp = None
        self.asset_list = []
        self.btc_quantity = {}
        self._env = None  #: shorted name
        self.env = {}  # type: Dict[str, Env]
        for idx in ["usdt", "btc"]:  # "busd"
            self.env[idx] = Env()  # should be initialized before reload()

        self._reload()
        # self.watchlist_mb = Mongo(mc, mc["watchlist"])
        for asset in ["usdt", "btc"]:
            self.env[asset].balance = Mongo(mc, mc[asset]["balance"])
            self.env[asset].balance_sum = Mongo(mc, mc[asset]["balance"])
            self.env[asset].hit = Mongo(mc, mc[asset]["hit"])
            self.env[asset].stats = Mongo(mc, mc[asset]["stats"])
            self.env[asset]._status = Mongo(mc, mc[asset]["status"])
            self.env[asset]._ts = Mongo(mc, mc[asset]["timestamp"])
            self.env[asset].estimated_balance = Mongo(mc, mc[asset]["estimated_balance"])
            if not self.env[asset]._status.find_one("count"):
                self.env[asset]._status.add_single_key("count", 0)

    def total_balance(self, _type) -> float:
        return float(self.env[_type].estimated_balance.find_one("total_balance")["value"])

    def estimated_balance(self) -> int:
        balance_brave = self.total_balance("usdt")
        balalance_chrome = self.total_balance("btc")
        return int(balance_brave + balalance_chrome)

    async def get_spot_timestamp(self, asset, symbol=None) -> int:
        """Returns asset's set timestamp and updates if it is not set."""
        key = f"{cfg.TYPE}_timestamp"
        if self.timestamp[key][asset] == {}:
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

            with suppress(Exception):
                for _, trade in enumerate(_trades):
                    log("config.get_spot_timestamp():", is_write=False)
                    t = trade.copy()
                    for key in ["info", "fee", "fees", "takerOrMaker", "type"]:
                        del t[key]

                    log(t, is_write=False)
                    if trade["info"]["isBuyer"]:
                        order_id = trade["info"]["orderId"]
                        first_orders = await exchange.spot.fetch_order_trades(order_id, symbol=symbol)
                        # at exact 20 seconds cycle large trades splitted and partially made
                        first_orders_ts = first_orders[0]["timestamp"]
                        break

                if 0 < first_orders_ts < _ts:
                    # update few seconds behind such as ts - 9
                    ts = first_orders_ts

            self.timestamp[key][asset] = ts

        return int(self.timestamp[key][asset])

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

    def _reload(self) -> None:
        self.cfg = self.yaml_wrapper(self.base_dir / "config.yaml", auto_dump=False)
        self.alerts = self.yaml_wrapper(self.base_dir / "alerts.yaml", auto_dump=False)
        self.watchlist = self.yaml_wrapper(self.base_dir / "watchlist.yaml", auto_dump=False)
        self.cfg_usdtperp = self.yaml_wrapper(self.base_dir / "config_usdtperp.yaml")
        self.timestamp = self.yaml_wrapper(self.base_dir / "timestamp.yaml")
        self.reload_wavetrend()
        self.goal = self.yaml_wrapper(self.base_dir / "goal.yaml")
        self.ALERTS = self.alerts["alerts"]
        self.WATCHLIST = self.watchlist["watch"]["list"]
        self.WATCHLIST_MSG = self.watchlist["watch"]["target"]
        self.take_profit = float(self.cfg["root"]["take_profit"]) + 0.0001
        self.discord_msg_above_usdt = self.cfg["root"]["discord_msg_above_usdt"]
        self.isolated_wallet_limit = self.cfg["root"]["isolated_wallet_limit"]
        self.is_manual_trade = self.cfg["root"]["is_manual_trade"]
        self.is_funding_rate_alert = self.cfg["root"]["is_funding_rate_alert"]
        for _type in ["usdt", "btc"]:  # "busd"
            self.env[_type].status = self.yaml_wrapper(self.base_dir / f"status_{_type}.yaml")
            self.env[_type].risk = self.yaml_wrapper(self.base_dir / f"risk_{_type}.yaml")["root"]
            self.env[_type].percent_change_to_add = -abs(self.cfg["root"][_type]["percent_change_to_add"]) + 0.01
            self.env[_type].multiply_ratio = self.cfg["root"][_type]["multiply_ratio"]
            self.env[_type].positions_alert = self.yaml_wrapper(self.base_dir / f"positions_alert_{_type}.yaml")
            self.env[_type].max_pos = self.cfg["root"][_type]["max_pos"]
            self.env[_type].isolated = self.cfg["root"][_type]["isolated"]

        self.SPOT_IGNORE_LIST = self.cfg["root"]["ignore"]
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.SPOT_locked_percent_limit = self.cfg["root"]["locked_percent_limit"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["root"]["btc"]["multiply_ratio"]
        self.initial_btc_quantity = self.cfg["root"]["btc"]["initial"]

    # BUSD
    # ====
    def get_spot_timestamp_busd(self, asset) -> int:
        key = "busd_timestamp"
        if self.timestamp[key][asset] == {}:
            self.timestamp[key][asset] = config.env["busd"].status["timestamp"]

        return int(self.timestamp[key][asset])

    # USDTPERP
    # ========
    def _reload_usdtperp(self) -> None:
        self.initialize_usdtperp()

    def initialize_usdtperp(self) -> None:
        self.USDTPERP_MULTIPLY_RATIO = None
        self.USDTPERP_MAX_POSITION = {}  # type: Dict[str, int]
        self.status_usdtperp = self.yaml_wrapper(self.base_dir / "usdtperp_pos_count.yaml")
        self._initial_usdt_qty_short = self.cfg_usdtperp["root"]["usdtperp"]["pos"]["short"]["base"]
        self.initial_usdt_qty_short["1m"] = self.cfg_usdtperp["root"]["usdtperp"]["pos"]["short"]["1m"]
        self._initial_usdt_qty_long = self.cfg_usdtperp["root"]["usdtperp"]["pos"]["long"]["base"]
        self.initial_usdt_qty_long["1m"] = self.cfg_usdtperp["root"]["usdtperp"]["pos"]["long"]["1m"]
        self.USDTPERP_PERCENT_CHANGE_TO_ADD = (
            -abs(self.cfg_usdtperp["root"]["usdtperp"]["percent_change_to_add"]) + 0.01
        )
        self.locked_per_limit_usdtperp = self.cfg_usdtperp["root"]["locked_percent_limit"]
        self.USDTPERP_MULTIPLY_RATIO = self.cfg_usdtperp["root"]["usdtperp"]["multiply_ratio"]
        self.USDTPERP_MAX_POSITION["9m"] = self.cfg_usdtperp["root"]["usdtperp"]["max_pos"]
        self.USDTPERP_MAX_POSITION["1m"] = self.cfg_usdtperp["root"]["usdtperp"]["max_pos"]
        self.USDTPERP_MAX_POSITION["21m"] = self.cfg_usdtperp["root"]["usdtperp"]["max_pos_21m"]


config: Config = Config()
exchange = Exchange()
