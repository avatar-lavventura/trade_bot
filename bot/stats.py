#!/usr/bin/env python3

from pymongo import MongoClient

from bot.mongodb import Mongo

if __name__ == "__main__":
    mc = MongoClient()
    # print("usdt")
    # mongo = Mongo(mc, mc["usdt"]["stats"])
    # mongo.find_all()

    print("btc")
    mongo = Mongo(mc, mc["btc"]["stats"])
    mongo.find_all(sort_str="timestamp")

    print("busd")
    mongo = Mongo(mc, mc["busd"]["stats"])
    mongo.find_all(sort_str="timestamp")
