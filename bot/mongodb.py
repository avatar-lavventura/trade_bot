#!/usr/bin/env python3

from broker.libs.mongodb import BaseMongoClass
from pymongo import MongoClient


class Mongo(BaseMongoClass):
    def add_item(self, symbol, ts, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol, "timestamp": ts}, item, True)
        return res.acknowledged

    def hit_count(self, symbol, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol}, item, True)
        return res.acknowledged


if __name__ == "__main__":
    mc = MongoClient()
    # mongo = Mongo(mc, mc["trader_bot"]["timestamp"])
    # output = mongo.add_item("alpy", 1000)
    mongo = Mongo(mc, mc["trader_bot"]["liq"])
    mongo.find_all(sort_str="timestamp")
