#!/usr/bin/env python3

from bot.user_setup import check_binance_obj


class Python_Binance:
    def __init__(self):
        self.client, self.balances = check_binance_obj()

    def transfer_futures_to_spot(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="2")

    def transfer_spot_to_futures(self, amount):
        self.client.futures_account_transfer(asset="USDT", amount=float(amount), type="1")

    def transfer_spot_to_margin(self, amount):
        self.client.transfer_spot_to_margin(asset="USDT", amount=float(amount), type="1")


if __name__ == "__main__":
    binance = Python_Binance()
    binance.transfer_futures_to_spot(400)
    # binance.transfer_spot_to_futures(252.43)
