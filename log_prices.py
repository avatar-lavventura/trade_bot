#!/usr/bin/env python3

from pathlib import Path

from binance_track import check_binance_obj

HOME = str(Path.home())


def get_all_prices(_symbol):
    agg_trades = client.aggregate_trade_iter(symbol=_symbol, start_str="1 day ago UTC")
    for trade in agg_trades:
        print(trade)


if __name__ == "__main__":
    client, balances = check_binance_obj()
    for balance in balances["balances"]:
        if balance["asset"] == "USDT":
            usdt_balance = balance["free"]
            break

    get_all_prices("BTCUSDT")
