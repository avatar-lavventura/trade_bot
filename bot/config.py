#!/usr/bin/env python3

from ebloc_broker.broker._utils.yaml import Yaml
from typing import Dict


class Config:
    def __init__(self) -> None:
        self.initial_usdt_qty_short = {}  # type: Dict[str, int]
        self.initial_usdt_qty_long = {}  # type: Dict[str, int]
        self.new_day = "03:00:00"
        self.fund_times = ["19:00:00", self.new_day, "11:00:00"]
        self.initialize()

    def reload(self) -> None:
        self.initialize()

    def get_spot_timestamp(self, asset):
        return self.timestamp["spot_timestamp"][asset]

    def total_position_count(self) -> int:
        return self.status["futures"]["pos_count"] + self.status["spot"]["pos_count"]

    def initialize(self) -> None:
        self.cfg = Yaml("config.yaml")
        self.timestamp = Yaml("timestamp.yaml")
        self.goal = Yaml("goal.yaml")
        self.status = Yaml("status.yaml")
        #
        self.TP = self.cfg["setup"]["TP"]
        self.trbinance_usdt = self.goal["goal"]["trbinance"]["usdt"]
        # spot
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["setup"]["spot"]["percent_change_to_add"]) + 0.01
        self.SPOT_locked_percent_limit = self.cfg["setup"]["spot"]["locked_percent_limit"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["setup"]["spot"]["multiply_ratio"]
        self.SPOT_MAX_POSITION_1m = self.cfg["setup"]["spot"]["max_pos_1m"]
        self.SPOT_MAX_POSITION = self.cfg["setup"]["spot"]["max_pos"]
        self.SPOT_IGNORE_LIST = self.cfg["setup"]["ignore"]["spot"]
        self.SPOT_TIMESTAMP = self.timestamp["spot_timestamp"]["BASE"]
        self.INITIAL_BTC_QTY = self.cfg["setup"]["spot"]["INITIAL_BTC_QTY"]
        # usdtperp
        self.USDTPERP_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["setup"]["usdtperp"]["percent_change_to_add"]) + 0.01
        self.locked_percent_limit_USDTPERP = self.cfg["setup"]["usdtperp"]["locked_percent_limit"]
        self.USDTPERP_MULTIPLY_RATIO = self.cfg["setup"]["usdtperp"]["multiply_ratio"]
        self.USDTPERP_MAX_POSITION_1m = self.cfg["setup"]["usdtperp"]["max_pos_1m"]
        self.USDTPERP_MAX_POSITION = self.cfg["setup"]["usdtperp"]["max_pos"]
        self.ignore_below_usdt = self.cfg["setup"]["ignore_below_usdt"]
        self.isolated_wallet_limit = self.cfg["setup"]["isolated_wallet_limit"]

        self._initial_usdt_qty_short = self.cfg["setup"]["usdtperp"]["pos"]["short"]["base"]
        self.initial_usdt_qty_short["1m"] = self.cfg["setup"]["usdtperp"]["pos"]["short"]["1m"]
        #
        self._initial_usdt_qty_long = self.cfg["setup"]["usdtperp"]["pos"]["long"]["base"]
        self.initial_usdt_qty_long["1m"] = self.cfg["setup"]["usdtperp"]["pos"]["long"]["1m"]

        # usdt
        self.usdt_percent_change_to_add = -abs(self.cfg["setup"]["usdt"]["percent_change_to_add"]) + 0.01
        self.usdt_multiply_ratio = self.cfg["setup"]["usdt"]["multiply_ratio"]


config: Config = Config()
