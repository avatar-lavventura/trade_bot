#!/usr/bin/env python3

from ebloc_broker.broker._utils.yaml import Yaml


class Config:
    def __init__(self) -> None:
        self.NEW_DAY = "03:00:00"
        self.FUND_TIMES = ["19:00:00", "03:00:00", "11:00:00"]
        self.initialize()

    def reload(self):
        self.initialize()

    def get_spot_timestamp(self, asset):
        return self.timestamp["spot_timestamp"][asset]

    def initialize(self):

        self.cfg = Yaml("config.yaml")

        self.timestamp = Yaml("timestamp.yaml")
        self.goal = Yaml("goal.yaml")
        self.status = Yaml("status.yaml")
        # spot
        self.SPOT_LOCKED_PERCENT_LIMIT = self.cfg["setup"]["spot"]["LOCKED_PERCENT_LIMIT"]
        self.SPOT_MULTIPLY_RATIO = self.cfg["setup"]["spot"]["MULTIPLY_RATIO"]
        self.SPOT_MAX_POSITION_1m = self.cfg["setup"]["spot"]["MAX_POSITION_1m"]
        self.SPOT_MAX_POSITION = self.cfg["setup"]["spot"]["MAX_POSITION"]
        self.SPOT_IGNORE_LIST = self.cfg["setup"]["spot"]["IGNORE_LIST"]
        self.SPOT_PERCENT_CHANGE_TO_ADD = -abs(self.cfg["setup"]["spot"]["PERCENT_CHANGE_TO_ADD"]) + 0.01
        self.SPOT_TIMESTAMP = self.timestamp["spot_timestamp"]["BASE"]
        self.INITIAL_BTC_QTY = self.cfg["setup"]["spot"]["INITIAL_BTC_QTY"]
        # futures
        self.trbinance_usdt = self.goal["goal"]["trbinance"]["usdt"]

        self.TP = self.cfg["setup"]["TP"]
        self.LOCKED_PERCENT_LIMIT_USDT = self.cfg["setup"]["LOCKED_PERCENT_LIMIT_USDT"]
        self.PERCENT_CHANGE_TO_ADD_USDT = -abs(self.cfg["setup"]["PERCENT_CHANGE_TO_ADD_USDT"]) + 0.01
        self.USDT_MULTIPLY_RATIO = self.cfg["setup"]["USDT_MULTIPLY_RATIO"]
        self.INITIAL_LEVERAGE = self.cfg["setup"]["INITIAL_LEVERAGE"]
        self.USDT_MAX_POSITION_1m = self.cfg["setup"]["USDT_MAX_POSITION_1m"]
        self.USDT_MAX_POSITION = self.cfg["setup"]["USDT_MAX_POSITION"]
        self.IGNORE_BELOW_USDT = self.cfg["setup"]["IGNORE_BELOW_USDT"]
        self.ISOLATED_WALLET_LIMIT = self.cfg["setup"]["ISOLATED_WALLET_LIMIT"]
        #
        self.INITIAL_USDT_QTY_SHORT_1m = self.cfg["setup"]["position"]["short"]["1m"]
        self.INITIAL_USDT_QTY_LONG_1m = self.cfg["setup"]["position"]["long"]["1m"]
        self.INITIAL_USDT_QTY_SHORT = self.cfg["setup"]["position"]["short"]["base"]
        self.INITIAL_USDT_QTY_LONG = self.cfg["setup"]["position"]["long"]["base"]


config: Config = Config()
