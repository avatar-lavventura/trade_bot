#!/usr/bin/env python3

from pprint import pprint

from pymongo import MongoClient


class BaseMongoClass:
    def __init__(self, mc, collection) -> None:
        self.mc = mc
        self.collection = collection

    def delete_all(self):
        return self.collection.delete_many({}).acknowledged

    def find_key(self, key, _key):
        output = self.collection.find_one({key: _key})
        if bool(output):
            return output
        else:
            raise

    def find_all(self):
        """Find_all."""
        cursor = self.collection.find({})
        for document in cursor:
            pprint(document)
        # print(document['_id'])
        # print(document['timestamp'])


class Mongo(BaseMongoClass):
    def __init__(self, mc, collection) -> None:
        super().__init__(mc, collection)

    def add_item(self, symbol, timestamp):
        """Adding job_key info along with its cache_duration into mongoDB."""
        item = {"symbol": symbol, "timestamp": timestamp}
        res = self.collection.replace_one({"symbol": symbol}, item, True)
        return res.acknowledged


if __name__ == "__main__":
    mc = MongoClient()
    mongo = Mongo(mc, mc["trader_bot"]["timestamp"])
    # output = mongo.add_item("alpy", 1000)
    mongo.find_all()
