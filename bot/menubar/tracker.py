#!/usr/bin/env python3

import subprocess

import ccxt
import rumps  # type: ignore

# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

# rumps.debug_mode(True)

sleep_duration = 10
exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
assets = ["BTCUSDT"]
# assets = assets + ["FTMUSDT", "SNMBTC", "SNMBUSD"]
assets = assets + ["SNMBTC", "SNMBUSD"]
for idx, asset in enumerate(reversed(assets)):
    try:
        output = exchange.fetch_ticker(asset)
    except Exception as e:
        if "binance does not have market symbol" in str(e):
            if "USDT" in asset:
                assets[idx] = asset.replace("USDT", "BUSD")


def run(cmd):
    return subprocess.check_output(cmd, shell=True).strip()


def tracker_clock_string():
    msg = ""
    for _, asset in enumerate(reversed(assets)):
        try:
            output = exchange.fetch_ticker(asset)
            price = output["last"]

            if asset == "SNMBUSD":
                price = "{:.3f}".format(price)
            else:
                asset = asset.replace("USDT", "")
                if price < 0.1:
                    price = "{:.8f}".format(price).strip("0.").lstrip("0")
                elif price > 1000:
                    price = round(price)
                elif price > 1:
                    price = "{:.4f}".format(price)

            if not msg:
                msg = f"{asset} {price}"
            else:
                msg = f"{asset} {price} | {msg}"
        except Exception as e:
            if "binance does not have market symbol" in str(e):
                print(f"E' {e}")

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
