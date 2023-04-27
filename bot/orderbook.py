#!/usr/bin/env python3

import asyncio
from decimal import Decimal

import ccxt.async_support as ccxt  # noqa: E402

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
exchange.number = Decimal


async def main():
    # await exchange.load_markets()
    while True:
        order_book_struct = await exchange.fetch_order_book("BTTCUSDT")
        bid_px, bid_amount = order_book_struct["bids"][0]
        ask_px, ask_amount = order_book_struct["asks"][0]
        ##
        order_book_struct = await exchange.fetch_order_book("BTTCBUSD")
        bid_px, bid_amount_busd = order_book_struct["bids"][0]
        ask_px, ask_amount_busd = order_book_struct["asks"][0]

        _amount = int((bid_amount + bid_amount_busd) * bid_px)
        _ask = int((ask_amount + ask_amount_busd) * bid_px)
        print(f"{_amount} bid at {bid_px!r}, {_ask} offered at {ask_px!r}")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
