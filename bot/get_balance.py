#!/usr/bin/env python3

from broker._utils.tools import log

from bot import cfg
from bot.client_helper import ClientHelper
from bot.trade_async import BotHelper, Strategy
from bot.user_setup import check_binance_obj

client, balances = check_binance_obj()
client_helper = ClientHelper(client)


def get_balance(client_helper):
    balances = client_helper.client.get_account()
    for balance in balances["balances"]:
        if balance["asset"] == "USDT":
            usdt_balance = balance["free"]
            break

    # margin_usdt = client_helper.get_balance_margin_usdt()
    # futures_usdt = client_helper._get_futures_usdtt()
    # futures_usdt = client_helper._get_futures_usdtt()
    log(f" * spot={client_helper._format(usdt_balance)} USD")
    client_helper.spot_balance()


def main():
    get_balance(client_helper)
    # bot = BotHelper(client_helper.client)
    # bot.strategy = Strategy()
    # # balances = client.get_account()
    # for _balance in balances["balances"]:
    #     asset = _balance["asset"]
    #     if (float(_balance["free"]) != 0.0 or float(_balance["locked"]) != 0.0) and asset not in cfg.STABLE_COINS:
    #         bot.strategy.symbol = asset + "BTC"
    #         bot.strategy.asset = asset
    #         log(f"==> {asset} ", end="")
    #         limit_price, *_ = bot.get_spot_entry()
    #         orders = bot.client.get_open_orders(symbol=bot.strategy.symbol)
    #         for order in orders:
    #             bot.client.cancel_order(symbol=bot.strategy.symbol, orderId=order["orderId"])

    #         order = bot.client.order_limit_sell(
    #             symbol=bot.strategy.symbol, price=str(limit_price), quantity=bot.asset_balance()
    #         )
    #         log(order)


if __name__ == "__main__":
    main()
