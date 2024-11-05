#!/usr/bin/env python3

import logging
from contextlib import suppress
from pathlib import Path

import discord
from _utils.tools import log
from _utils.yaml import Yaml

from bot import cfg

logger = logging.getLogger("discord")
logger.setLevel(logging.CRITICAL)


class DiscordClient:
    def __init__(self):
        _config = Yaml(Path.home() / ".binance.yaml")
        self.bot = discord.Client(intents=discord.Intents.default())
        self.TOKEN = _config["discord"]["TOKEN"]
        self.channel_name = _config["discord"]["CHANNEL_NAME"]
        self.channel = {}

    async def send_msg(self, msg="OK", channel_name=""):
        await self.bot.wait_until_ready()
        if not channel_name:
            channel_name = self.channel_name

        if channel_name not in self.channel:
            self.channel[channel_name] = discord.utils.get(self.bot.get_all_channels(), name=channel_name)

        await self.channel[channel_name].send(msg)


class ClientHelper:
    def __init__(self, client):
        self.client = client

    def _format(self, value, decimal=2):
        return format(float(value), f".{decimal}f")

    def transfer_spot_to_futures(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="1")

    def transfer_spot_to_margin(self, amount):
        self.client.transfer_spot_to_margin(asset="USDT", amount=float(amount), type="1")

    def transfer_futures_to_spot(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="2")

    def get_balance_margin_usdt(self) -> float:
        with suppress(Exception):
            for idx in range(len(self.client.get_margin_account()["userAssets"])):
                if self.client.get_margin_account()["userAssets"][idx]["asset"] == "USDT":
                    balance_usdt = self.client.get_margin_account()["userAssets"][idx]["free"]
                    return float(balance_usdt)

        return 0.0

    def spot_balance(self, balances=None) -> None:
        sum_btc = 0.0
        if not balances:
            balances = self.client.get_account()

        for balance in balances["balances"]:
            asset = balance["asset"]
            if float(balance["free"]) != 0.0 or float(balance["locked"]) != 0.0:
                with suppress(Exception):
                    btc_quantity = float(balance["free"]) + float(balance["locked"])
                    if asset == "BTC":
                        sum_btc += btc_quantity
                    else:
                        _price = self.client.get_symbol_ticker(symbol=asset + "BTC")
                        sum_btc += btc_quantity * float(_price["price"])

        current_btc_price_USD = self.client.get_symbol_ticker(symbol="BTCUSDT")["price"]
        own_usdt = sum_btc * float(current_btc_price_USD)
        log(" * Spot => %.8f BTC [blue]==[/blue] " % sum_btc, end="")
        log("%.8f USDT" % own_usdt)

    def get_futures_usdt(self, is_both=True) -> float:
        futures_usd = 0.0
        for asset in self.client.futures_account_balance():
            name = asset["asset"]
            balance = float(asset["balance"])
            if name == "USDT":
                futures_usd += balance

            if name == "BNB" and is_both:
                futures_usd += balance * cfg.BNBUSDT

        return float(futures_usd)

    def _get_futures_usdt(self):
        """USDT in Futures, unRealizedProfit is also included."""
        futures_usd = self.get_futures_usdt(is_both=False)
        futures = self.client.futures_position_information()
        for future in futures:
            if future["positionAmt"] != "0" and float(future["unRealizedProfit"]) != 0.00000000:
                futures_usd += float(future["unRealizedProfit"])

        return format(futures_usd, ".2f")
