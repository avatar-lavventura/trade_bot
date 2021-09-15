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
        self.config = Yaml("config.yaml")
        self.timestamp = Yaml("timestamp.yaml")
        self.goal = Yaml("goal.yaml")
        self.status = Yaml("status.yaml")
        #
        self.TRBINANCE_USDT = self.config["TRBINANCE"]["USDT"]
        self.SPOT_TIMESTAMP = self.timestamp["spot_timestamp"]["BASE"]
        self.TP = self.config["setup"]["TP"]
        self.LOCKED_PERCENT_LIMIT_USDT = self.config["setup"]["LOCKED_PERCENT_LIMIT_USDT"]
        self.LOCKED_PERCENT_LIMIT_SPOT = self.config["setup"]["LOCKED_PERCENT_LIMIT_SPOT"]
        self.PERCENT_CHANGE_TO_ADD_USDT = self.config["setup"]["PERCENT_CHANGE_TO_ADD_USDT"]
        self.PERCENT_CHANGE_TO_ADD_SPOT = self.config["setup"]["PERCENT_CHANGE_TO_ADD_SPOT"]
        self.SPOT_MULTIPLY_RATIO = self.config["setup"]["SPOT_MULTIPLY_RATIO"]
        self.USDT_MULTIPLY_RATIO = self.config["setup"]["USDT_MULTIPLY_RATIO"]
        self.IGNORE_LIST_SPOT = self.config["setup"]["IGNORE_LIST_SPOT"]
        self.INITIAL_USDT_QTY_SHORT = self.config["position"]["short"]["base"]
        self.INITIAL_USDT_QTY_LONG = self.config["position"]["long"]["base"]
        self.INITIAL_BTC_QTY = self.config["setup"]["INITIAL_BTC_QTY"]
        self.INITIAL_LEVERAGE = self.config["setup"]["INITIAL_LEVERAGE"]
        self.SPOT_MAX_POSITION_NUMBER = self.config["setup"]["SPOT_MAX_POSITION_NUMBER"]
        self.USDT_MAX_POSITION_NUMBER = self.config["setup"]["USDT_MAX_POSITION_NUMBER"]
        self.IGNORE_BELOW_USDT = self.config["setup"]["IGNORE_BELOW_USDT"]


config: Config = Config()
