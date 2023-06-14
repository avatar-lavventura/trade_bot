#!/usr/bin/env python3

import subprocess

import ccxt
import rumps  # type: ignore
from pycoingecko import CoinGeckoAPI

# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

# rumps.debug_mode(True)

is_motivation_msg = True
exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
assets = ["BTCUSDT", "USDTTRY"]
assets += ["BONDBUSD", "BONDBTC"]

# MSG = "binance: We are unable to provide any donation -- makes you angry."
MSG = "The most important rule in trading is to protect your capital at all cost."

cg = CoinGeckoAPI()
for idx, asset in enumerate(reversed(assets)):
    try:
        output = exchange.fetch_ticker(asset)
    except Exception as e:
        if "binance does not have market symbol" in str(e):
            if "USDT" in asset:
                assets[idx] = asset.replace("USDT", "BUSD")
            elif "USDT" in asset:
                assets[idx] = asset.replace("BTC", "BUSD")


def run(cmd):
    return subprocess.check_output(cmd, shell=True).strip()


def orderbook() -> str:
    order_book_struct = exchange.fetch_order_book("BTTCUSDT")
    bid_px, bid_amount = order_book_struct["bids"][0]
    ask_px, ask_amount = order_book_struct["asks"][0]
    #
    order_book_struct = exchange.fetch_order_book("BTTCBUSD")
    bid_px, bid_amount_busd = order_book_struct["bids"][0]
    ask_px, ask_amount_busd = order_book_struct["asks"][0]

    _amount = int((bid_amount + bid_amount_busd) * bid_px)
    _ask = int((ask_amount + ask_amount_busd) * bid_px)
    _bid_px = "{:.8f}".format(bid_px).lstrip("0.").lstrip("0")
    _ask_px = "{:.8f}".format(ask_px).lstrip("0.").lstrip("0")
    text = f"{_bid_px}({_amount}) ?= {_ask_px}({_ask})"
    return text


def tracker_clock_string():
    msg = ""
    text = ""
    for _, asset in enumerate(reversed(assets)):
        btcusdt = 0
        price = ""
        if asset == "":
            continue

        if asset == "COMBOBTC":
            price = cg.get_price(ids="cocos-bcx", vs_currencies="btc")
            price = "{:.8f}".format(price["cocos-bcx"]["btc"]).strip("0.").lstrip("0")
        else:
            try:
                if asset == "BTTCUSDT":
                    # here price is fetched from BTTCTRY pair since its more correct
                    asset_price = exchange.fetch_ticker("BTTCTRY")
                    USDTTRY = exchange.fetch_ticker("USDTTRY")
                    price = float(format(asset_price["last"] / USDTTRY["last"], ".10f"))
                else:
                    _price = exchange.fetch_ticker(asset)
                    price = (_price["bid"] + _price["ask"]) / 2  # was: _price["last"]

                asset = asset.replace("USDT", "").replace("BUSD", "")
                if 1 <= price <= 10:
                    price = "{:.3f}".format(price)
                elif 0.1 <= price <= 1:
                    price = "{:.4f}".format(price)
                elif 10 <= price <= 100:
                    price = "{:.2f}".format(price)
                else:
                    if price < 0.1:
                        if asset == "BTTC":
                            price = "{:.10f}".format(price).lstrip("0.").lstrip("0")
                        else:
                            price = "{:.8f}".format(price).lstrip("0.").lstrip("0")
                            if asset == "BONDBTC":
                                price = round(int(price) / 10)

                    elif price > 1000:
                        price = round(price)
                    elif price > 1:
                        price = "{:.4f}".format(price)
            except Exception as e:
                if "binance does not have market symbol" in str(e):
                    print(f"E' {e}")

        if asset == "BTTC":
            text = orderbook()

        if msg:
            if asset == "BTC":
                btcusdt = price
                msg = f"{price} | {msg}"
            else:
                msg = f"{asset} {price} | {msg}"
        else:
            if asset == "BTC":
                btcusdt = price
                msg = f"{price}"
            else:
                msg = f"{asset} {price}"

        if is_motivation_msg:
            if btcusdt:
                if text:
                    msg = f"{MSG} {msg} // {text} "
                else:
                    msg = f"{MSG} {msg} "
        else:
            msg = "❗ no-internet ❗"

    return msg


class OrgClockStatusBarApp(rumps.App):
    @rumps.clicked("Refresh")
    def update_ticker(self, _):
        self.title = tracker_clock_string()


def main():
    app = OrgClockStatusBarApp("starting... ")

    def timer_func(_):
        _str = tracker_clock_string()
        print(_str)  # removing the print statement makes the app hang
        if _str:
            app.title = _str
        else:
            app.title = "Not tracking"

    timer = rumps.Timer(timer_func, interval=20)
    timer.start()
    app.run()


if __name__ == "__main__":
    main()
