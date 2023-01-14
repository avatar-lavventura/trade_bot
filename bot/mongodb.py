#!/usr/bin/env python3

from pymongo import MongoClient

from ebloc_broker.broker.libs.mongodb import BaseMongoClass


class Mongo(BaseMongoClass):
    def add_item(self, symbol, timestamp, item):
        """Add symbol along with its portfolio into mongo_db."""
        res = self.collection.replace_one({"symbol": symbol, "timestamp": timestamp}, item, True)
        return res.acknowledged


if __name__ == "__main__":
    mc = MongoClient()
    # mongo = Mongo(mc, mc["trader_bot"]["timestamp"])
    # output = mongo.add_item("alpy", 1000)
    mongo = Mongo(mc, mc["trader_bot"]["liq"])
    mongo.find_all(sort_str="timestamp")
