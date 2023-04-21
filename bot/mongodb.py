#!/usr/bin/env python3

# from broker._utils.tools import _date
from broker.libs.mongodb import BaseMongoClass
from pymongo import MongoClient


class Mongo(BaseMongoClass):
    def add_single_key(self, key, value):
        """Add, if exists replace, key along with its portfolio into mongo_db."""
        item = {"key": key, "value": value}
        res = self.collection.replace_one({"key": key}, item, True)
        return res.acknowledged

    def find_one(self, key):
        return self.collection.find_one({"key": key})

    def _inc(self, key, value=1):
        """Add key along with its portfolio into mongo_db."""
        output = self.collection.find_one({"key": key})
        if not output:
            self.add_single_key(key, value)
            return True
        else:
            res = self.collection.update_one({"_id": output["_id"]}, {"$inc": {"value": 1}}, True)
            return res.acknowledged

    def add_item(self, key, ts, item):
        """Add key along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"key": key, "timestamp": ts}, item, True)
        return res.acknowledged

    def hit_count(self, key, item):
        """Add key along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"key": key}, item, True)
        return res.acknowledged


def liq_data():
    mongo = Mongo(mc, mc["trader_bot"]["liq"])
    mongo.find_all(sort_str="timestamp")


def get_latest_ts():
    mongo = Mongo(mc, mc["btc"]["timestamp"])
    # mongo.add_single_key("latest", 99)
    print(mongo.find_one("latest")["value"])


if __name__ == "__main__":
    mc = MongoClient()
    # mongo = Mongo(mc, mc["trader_bot"]["timestamp"])
    # output = mongo.add_item("alpy", 1000)
    # liq_data()
    #
    # mongo = Mongo(mc, mc["btc"]["hit"])
    # # mongo._inc("DOGE")
    # output = mongo.find_one("DOGE")
    # print(output["value"])

    # # mongo.add_single_key("doo", {"key": "doo", "value": 1})
    # mongo = Mongo(mc, mc["btc"]["value"])
    # current_date = _date(_type="month-day")
    # mongo._inc(current_date)
    # mongo.find_all(sort_str="timestamp")

    # mongo = Mongo(mc, mc["btc"]["status"])
    # # output = mongo.add_single_key("count", 3)
    # # mongo._inc("count")
    # # output = mongo.find_one("count")
    # # print(output["value"])
    # mongo.find_all(sort_str="timestamp")
    #
    get_latest_ts()
    print("done")
