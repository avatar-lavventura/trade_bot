#!/usr/bin/env python3

import os
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Dict

from broker._utils.yaml import Yaml
from filelock import FileLock
from pymongo import MongoClient

from bot import cfg
from bot.mongodb import Mongo

mc = MongoClient()


class Env:
    def __init__(self):
        self.percent_change_to_add = None
        self.usdt_multiply_ratio = None
        self.hit = None
        self.risk = None
        self.stats = None
        self.status = None
        self.multiply_ratio = 1.0


class Config:
    def __init__(self) -> None:
        self.env = {}  # type: Dict[str, Env]
        self.env["usdt"] = Env()
        self.env["btc"] = Env()
        self.env["busd"] = Env()
        self.base_dir = Path.home() / ".bot"
        self.initial_usdt_qty_short = {}  # type: Dict[str, int]
        self.initial_usdt_qty_long = {}  # type: Dict[str, int]
        self.USDTPERP_MAX_POSITION = {}  # type: Dict[str, int]
        self.base_durations = ["9m", "15m", "21m"]
        self.sum_usdt: float = 0.0
        self.locked_per_limit_usdtperp = None
        self.USDTPERP_MULTIPLY_RATIO = None
        self.btc_wavetrend = {}  # type: Dict[str, str]
        self.asset_list = []
        self.btc_quantity = {}
        self._reload()
        for asset in ["usdt", "btc", "busd"]:
            self.env[asset].hit = Mongo(mc, mc[asset]["hit"])
            self.env[asset].stats = Mongo(mc, mc[asset]["stats"])

    def get_spot_timestamp(self, asset):
        key = f"{cfg.TYPE}_timestamp"
        if self.timestamp[key][asset] == {}:
            self.timestamp[key][asset] = config.env[cfg.TYPE].status["timestamp"]

        return int(self.timestamp[key][asset])

    def get_spot_timestamp_busd(self, asset):
        key = "busd_timestamp"
        if self.timestamp[key][asset] == {}:
            self.timestamp[key][asset] = config.env["busd"].status["timestamp"]

        return int(self.timestamp[key][asset])

    def _yaml_wrapper(self, path, dirname, fn, auto_dump=True):
        if fn[0] == ".":
            fp_lockname = f"initialize_{fn}.lock"
        else:
            fp_lockname = f".initialize_{fn}.lock"

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
        self.WATCHLIST = self.watchlist["watchlist"]
        self.take_profit = float(self.cfg["root"]["take_profit"]) + 0.0001
        self.discord_msg_above_usdt = self.cfg["root"]["discord_msg_above_usdt"]
        self.isolated_wallet_limit = self.cfg["root"]["isolated_wallet_limit"]

        self.env["usdt"].status = self.yaml_wrapper(self.base_dir / "status_usdt.yaml")
        self.env["usdt"].risk = self.yaml_wrapper(self.base_dir / "risk_usdt.yaml")["root"]
        self.env["usdt"].percent_change_to_add = -abs(self.cfg["root"]["usdt"]["percent_change_to_add"]) + 0.01
        self.env["usdt"].multiply_ratio = self.cfg["root"]["usdt"]["multiply_ratio"]
        self.env["usdt"].positions_alert = self.yaml_wrapper(self.base_dir / "positions_alert_usdt.yaml")

        self.env["busd"].status = self.yaml_wrapper(self.base_dir / "status_busd.yaml")
        self.env["busd"].risk = self.yaml_wrapper(self.base_dir / "risk_busd.yaml")["root"]
        self.env["busd"].percent_change_to_add = -abs(self.cfg["root"]["busd"]["percent_change_to_add"]) + 0.01
        self.env["busd"].multiply_ratio = self.cfg["root"]["busd"]["multiply_ratio"]
        self.env["busd"].positions_alert = self.yaml_wrapper(self.base_dir / "positions_alert_busd.yaml")

        self.env["btc"].status = self.yaml_wrapper(self.base_dir / "status_btc.yaml")
        self.env["btc"].risk = self.yaml_wrapper(self.base_dir / "risk_btc.yaml")["root"]
        self.env["btc"].percent_change_to_add = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.env["btc"].multiply_ratio = self.cfg["root"]["btc"]["multiply_ratio"]
        self.env["btc"].positions_alert = self.yaml_wrapper(self.base_dir / "positions_alert_btc")

        self.status_usdtperp = self.yaml_wrapper(self.base_dir / "usdtperp_pos_count.yaml")
        self.status_usdt = self.yaml_wrapper(self.base_dir / "usdt_pos_count.yaml")
        self.status_btc = self.yaml_wrapper(self.base_dir / "btc_pos_count.yaml")

        # spot
        # ====
        self.SPOT_IGNORE_LIST = self.cfg["root"]["ignore"]
        self.USDT_MAX_POS = self.cfg["root"]["usdt"]["max_pos"]
        self.BTC_MAX_POS = self.cfg["root"]["btc"]["max_pos"]
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.SPOT_locked_percent_limit = self.cfg["root"]["locked_percent_limit"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["root"]["btc"]["multiply_ratio"]
        self.initial_btc_quantity = self.cfg["root"]["btc"]["initial"]
        # self.initialize_usdtperp()

    def initialize_usdtperp(self) -> None:
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
