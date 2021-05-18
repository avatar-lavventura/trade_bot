#!/usr/bin/env python3

import logging
from pathlib import Path

import discord

from ebloc_broker.broker._utils.tools import log
from ebloc_broker.broker._utils.yaml import Yaml

logger = logging.getLogger("discord")
logger.setLevel(logging.CRITICAL)


class DiscordClient:
    def __init__(self):
        _config = Yaml(Path(f"{Path.home()}/.binance.yaml"))
        self.bot = discord.Client()
        self.TOKEN = _config["discord"]["TOKEN"]
        self.channel_id = _config["discord"]["CHANNEL_ALPY"]

    async def send_message(self, msg="OK"):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.channel_id)
        await channel.send(msg)


class ClientHelper:
    def __init__(self, client):
        self.client = client

    def _format(self, value, decimal=2):
        return format(float(value), ".2f")

    def transfer_futures_to_spot(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="2")

    def transfer_spot_to_futures(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="1")

    def transfer_spot_to_margin(self, amount):
        self.client.transfer_spot_to_margin(asset="USDT", amount=float(amount), type="1")

    def get_balance_margin_USDT(self):
        try:
            _len = len(self.client.get_margin_account()["userAssets"])
            for x in range(_len):
                if self.client.get_margin_account()["userAssets"][x]["asset"] == "USDT":
                    balance_USDT = self.lient.get_margin_account()["userAssets"][x]["free"]
                    return float(balance_USDT)
        except:
            pass

        return 0

    def spot_balance(self, balances=None):
        sum_btc = 0.0
        if not balances:
            balances = self.client.get_account()

        for balance in balances["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                try:
                    btc_quantity = float(balance["free"]) + float(balance["locked"])
                    if asset == "BTC":
                        sum_btc += btc_quantity
                    else:
                        _price = self.client.get_symbol_ticker(symbol=asset + "BTC")
                        sum_btc += btc_quantity * float(_price["price"])
                except:
                    pass

        current_btc_price_USD = self.client.get_symbol_ticker(symbol="BTCUSDT")["price"]
        own_usd = sum_btc * float(current_btc_price_USD)
        log(" * Spot => %.8f BTC == " % sum_btc, end="")
        log("%.8f USDT" % own_usd)

    def get_futures_usdt(self, is_both=True) -> float:
        futures_usd = 0.0
        for asset in self.client.futures_account_balance():
            name = asset["asset"]
            balance = float(asset["balance"])
            if name == "USDT":
                futures_usd += balance

            if name == "BNB" and is_both:
                current_bnb_price_USD = self.client.get_symbol_ticker(symbol="BNBUSDT")["price"]
                futures_usd += balance * float(current_bnb_price_USD)

        return float(futures_usd)

    def _get_futures_usdt(self):
        """USDT in Futures, unRealizedProfit is also included."""
        futures_usd = self.get_futures_usdt(is_both=False)
        futures = self.client.futures_position_information()
        for future in futures:
            if future["positionAmt"] != "0" and float(future["unRealizedProfit"]) != 0.00000000:
                futures_usd += float(future["unRealizedProfit"])

        return format(futures_usd, ".2f")
