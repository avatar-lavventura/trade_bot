#!/usr/bin/env python3

import os
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Dict

from broker._utils.yaml import Yaml
from filelock import FileLock

from bot import cfg


class Config:
    def __init__(self) -> None:
        class Env:
            def __init__(self):
                self.percent_change_to_add = None
                self.usdt_multiply_ratio = None
                self.hit = None
                self.risk = None
                self.stats = None
                self.status = None
                self.multiply_ratio = 1

        self.env = {}  # type: Dict[str, Env]
        self.env["usdt"] = Env()
        self.env["btc"] = Env()

        self.base_dir = Path.home() / ".bot"
        self.initial_usdt_qty_short = {}  # type: Dict[str, int]
        self.initial_usdt_qty_long = {}  # type: Dict[str, int]
        self.USDTPERP_MAX_POSITION = {}  # type: Dict[str, int]
        self.new_day = "03:00:00"
        self.fund_times = ["19:00:00", self.new_day, "11:00:00"]
        self.base_durations = ["9m", "15m", "21m"]
        self.sum_usdt: float = 0
        self.locked_per_limit_usdtperp = None
        self.USDTPERP_MULTIPLY_RATIO = None
        self.white_list = []
        self.asset_list = []
        self.btc_quantity = {}
        self.initialize()
        self.env["usdt"].hit = self.yaml_wrapper(self.base_dir / "hit_usdt.yaml")["root"]
        self.env["usdt"].stats = self.yaml_wrapper(self.base_dir / "stats_usdt.yaml")
        self.env["btc"].stats = self.yaml_wrapper(self.base_dir / "stats_btc.yaml")
        self.env["btc"].hit = self.yaml_wrapper(self.base_dir / "hit_btc.yaml")["root"]

    def reload(self) -> None:
        self.initialize()

    def get_spot_timestamp(self, asset):
        key = f"{cfg.TYPE.lower()}_timestamp"
        if self.timestamp[key][asset] == {}:
            self.timestamp[key][asset] = self.run_balance["root"]["timestamp"]

        return int(self.timestamp[key][asset])

    # def total_position_count(self) -> int:
    #     return self.status["futures"]["pos_count"] + self.status_usdt["count"]

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

    def initialize(self) -> None:
        self.cfg = self.yaml_wrapper(self.base_dir / "config.yaml", auto_dump=False)
        self.alerts = self.yaml_wrapper(self.base_dir / "alerts.yaml", auto_dump=False)
        self.cfg_usdtprep = self.yaml_wrapper(self.base_dir / "config_usdtprep.yaml")
        self.timestamp = self.yaml_wrapper(self.base_dir / "timestamp.yaml")
        self.run_balance = self.yaml_wrapper(self.base_dir / "run_balance.yaml")
        self.goal = self.yaml_wrapper(self.base_dir / "goal.yaml")
        self.ALERTS = self.alerts["alerts"]
        self._initial_usdt_qty = self.cfg_usdtprep["root"]["usdtperp"]["pos"]["long"]["base"]
        self.take_profit = float(self.cfg["root"]["take_profit"]) + 0.0001
        self.discord_msg_above_usdt = self.cfg["root"]["discord_msg_above_usdt"]
        self.isolated_wallet_limit = self.cfg["root"]["isolated_wallet_limit"]

        self.env["usdt"].status = self.yaml_wrapper(self.base_dir / "status_usdt.yaml")
        self.env["usdt"].percent_change_to_add = -abs(self.cfg["root"]["usdt"]["percent_change_to_add"]) + 0.01
        self.env["usdt"].multiply_ratio = self.cfg["root"]["usdt"]["multiply_ratio"]
        self.env["usdt"].risk = self.yaml_wrapper(self.base_dir / "risk_usdt.yaml")["root"]

        self.env["btc"].status = self.yaml_wrapper(self.base_dir / "status_btc.yaml")
        self.env["btc"].percent_change_to_add = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.env["btc"].multiply_ratio = self.cfg["root"]["btc"]["multiply_ratio"]
        self.env["btc"].risk = self.yaml_wrapper(self.base_dir / "risk_btc.yaml")["root"]

        self.status_usdtperp = self.yaml_wrapper(self.base_dir / "usdtperp_pos_count.yaml")
        self.status_usdt = self.yaml_wrapper(self.base_dir / "usdt_pos_count.yaml")
        self.status_btc = self.yaml_wrapper(self.base_dir / "btc_pos_count.yaml")

        # spot
        # ====
        self.USDT_MAX_POSITION = self.cfg["root"]["usdt"]["max_pos"]
        self.BTC_MAX_POSITION = self.cfg["root"]["btc"]["max_pos"]

        self.SPOT_TIMESTAMP = self.run_balance["root"]["timestamp"]
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["root"]["btc"]["percent_change_to_add"]) + 0.01
        self.SPOT_locked_percent_limit = self.cfg["root"]["locked_percent_limit"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["root"]["btc"]["multiply_ratio"]
        self.initial_btc_quantity = self.cfg["root"]["btc"]["initial"]

        self.SPOT_IGNORE_LIST = self.cfg["root"]["ignore"]
        # self.initialize_usdtprep()

    def initialize_usdtprep(self) -> None:
        self._initial_usdt_qty_short = self.cfg_usdtprep["root"]["usdtperp"]["pos"]["short"]["base"]
        self.initial_usdt_qty_short["1m"] = self.cfg_usdtprep["root"]["usdtperp"]["pos"]["short"]["1m"]
        self._initial_usdt_qty_long = self.cfg_usdtprep["root"]["usdtperp"]["pos"]["long"]["base"]
        self.initial_usdt_qty_long["1m"] = self.cfg_usdtprep["root"]["usdtperp"]["pos"]["long"]["1m"]
        self.USDTPERP_PERCENT_CHANGE_TO_ADD = (
            -abs(self.cfg_usdtprep["root"]["usdtperp"]["percent_change_to_add"]) + 0.01
        )
        self.locked_per_limit_usdtperp = self.cfg_usdtprep["root"]["locked_percent_limit"]
        self.USDTPERP_MULTIPLY_RATIO = self.cfg_usdtprep["root"]["usdtperp"]["multiply_ratio"]
        self.USDTPERP_MAX_POSITION["9m"] = self.cfg_usdtprep["root"]["usdtperp"]["max_pos"]
        self.USDTPERP_MAX_POSITION["1m"] = self.cfg_usdtprep["root"]["usdtperp"]["max_pos"]
        self.USDTPERP_MAX_POSITION["21m"] = self.cfg_usdtprep["root"]["usdtperp"]["max_pos_21m"]


config: Config = Config()
