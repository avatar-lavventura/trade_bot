#!/usr/bin/env python3

from ebloc_broker.broker._utils.yaml import Yaml


class Config:
    def __init__(self) -> None:
        self.NEW_DAY = "03:00:00"
        self.FUND_TIMES = ["19:00:00", "03:00:00", "11:00:00"]
        self.initialize()

    def reload(self) -> None:
        self.initialize()

    def get_spot_timestamp(self, asset):
        return self.timestamp["spot_timestamp"][asset]

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
        self.SPOT_LOCKED_PERCENT_LIMIT = self.cfg["setup"]["spot"]["LOCKED_PERCENT_LIMIT"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["setup"]["spot"]["multiply_ratio"]
        self.SPOT_MAX_POSITION_1m = self.cfg["setup"]["spot"]["max_pos_1m"]
        self.SPOT_MAX_POSITION = self.cfg["setup"]["spot"]["max_pos"]
        self.SPOT_IGNORE_LIST = self.cfg["setup"]["ignore"]["spot"]
        self.SPOT_TIMESTAMP = self.timestamp["spot_timestamp"]["BASE"]
        self.INITIAL_BTC_QTY = self.cfg["setup"]["spot"]["INITIAL_BTC_QTY"]
        # usdtperp
        self.USDTPERP_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["setup"]["usdtperp"]["percent_change_to_add"]) + 0.01
        self.LOCKED_PERCENT_LIMIT_USDTPERP = self.cfg["setup"]["LOCKED_PERCENT_LIMIT_USDT"]
        self.USDTPERP_MULTIPLY_RATIO = self.cfg["setup"]["usdtperp"]["multiply_ratio"]
        self.USDTPERP_MAX_POSITION_1m = self.cfg["setup"]["usdtperp"]["max_pos_1m"]
        self.USDTPERP_MAX_POSITION = self.cfg["setup"]["usdtperp"]["max_pos"]
        self.IGNORE_BELOW_USDT = self.cfg["setup"]["IGNORE_BELOW_USDT"]
        self.ISOLATED_WALLET_LIMIT = self.cfg["setup"]["ISOLATED_WALLET_LIMIT"]
        self.INITIAL_USDT_QTY_SHORT_1m = self.cfg["setup"]["usdtperp"]["pos"]["short"]["1m"]
        self.INITIAL_USDT_QTY_LONG_1m = self.cfg["setup"]["usdtperp"]["pos"]["long"]["1m"]
        self.INITIAL_USDT_QTY_SHORT = self.cfg["setup"]["usdtperp"]["pos"]["short"]["base"]
        self.INITIAL_USDT_QTY_LONG = self.cfg["setup"]["usdtperp"]["pos"]["long"]["base"]
        # usdt
        self.usdt_percent_change_to_add = -abs(self.cfg["setup"]["usdt"]["percent_change_to_add"]) + 0.01
        self.usdt_multiply_ratio = self.cfg["setup"]["usdt"]["multiply_ratio"]


config: Config = Config()
