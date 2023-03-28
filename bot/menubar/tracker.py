#!/usr/bin/env python3

import subprocess

import ccxt
import rumps  # type: ignore
from pycoingecko import CoinGeckoAPI

# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

# rumps.debug_mode(True)

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
assets = ["BTCUSDT"]
assets = assets + ["COCOSUSDT", "COCOSBTC"]
sleep_duration = 20
is_quote = True
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


def tracker_clock_string():
    msg = ""
    for _, asset in enumerate(reversed(assets)):
        if asset == "COCOSBTC":
            price = cg.get_price(ids="cocos-bcx", vs_currencies="btc")
            price = "{:.8f}".format(price["cocos-bcx"]["btc"]).strip("0.").lstrip("0")
        else:
            try:
                output = exchange.fetch_ticker(asset)
                price = output["last"]
                if 1 <= price <= 10:
                    price = "{:.3f}".format(price)
                else:
                    asset = asset.replace("USDT", "")
                    if price < 0.1:
                        price = "{:.8f}".format(price).strip("0.").lstrip("0")
                    elif price > 1000:
                        price = round(price)
                    elif price > 1:
                        price = "{:.4f}".format(price)
            except Exception as e:
                if "binance does not have market symbol" in str(e):
                    print(f"E' {e}")

        if msg:
            if asset == "BTC":
                msg = f"{price} | {msg}"
            else:
                msg = f"{asset} {price} | {msg}"
        else:
            msg = f"{asset} {price}"

    if is_quote:
        msg = f"{MSG} {msg}"

    return f"{msg} "


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

    timer = rumps.Timer(timer_func, sleep_duration)
    timer.start()
    app.run()


if __name__ == "__main__":
    main()
