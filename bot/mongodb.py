#!/usr/bin/env python3

from broker.libs.mongodb import BaseMongoClass
from pymongo import MongoClient


class Mongo(BaseMongoClass):
    def add_single_key(self, symbol, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol}, item, True)
        return res.acknowledged

    def _inc(self, symbol):
        """Add symbol along with its portfolio into mongo_db."""
        output = self.collection.find_one({"symbol": symbol})
        if not output:
            self.add_single_key("doo", {"symbol": symbol, "stats": 1})
            return True
        else:
            res = self.collection.update_one({"_id": output["_id"]}, {"$inc": {"stats": 1}}, True)
            return res.acknowledged

    def add_item(self, symbol, ts, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol, "timestamp": ts}, item, True)
        return res.acknowledged

    def hit_count(self, symbol, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol}, item, True)
        return res.acknowledged


def liq_data():
    mongo = Mongo(mc, mc["trader_bot"]["liq"])
    mongo.find_all(sort_str="timestamp")


if __name__ == "__main__":
    mc = MongoClient()
    # mongo = Mongo(mc, mc["trader_bot"]["timestamp"])
    # output = mongo.add_item("alpy", 1000)
    # liq_data()
    #
    mongo = Mongo(mc, mc["btc"]["stats"])
    # mongo._inc("doodoo")
    # mongo.add_single_key("doo", {"symbol": "doo", "stats": 1})
    mongo.find_all()
