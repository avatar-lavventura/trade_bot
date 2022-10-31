#!/usr/bin/env python3

# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

import ccxt
import rumps  # type: ignore
import subprocess

# rumps.debug_mode(True)
interval = 20
exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
assets = ["BTCUSDT"]
assets = assets + ["SNMBTC", "SNMBUSD"]
for idx, asset in enumerate(reversed(assets)):
    try:
        output = exchange.fetch_ticker(asset)
    except Exception as e:
        if "binance does not have market symbol" in str(e):
            if "USDT" in asset:
                assets[idx] = asset.replace("USDT", "BUSD")


# assets = assets + ["DOGEBTC", "DOGEUSDT"]
#
# sold_asset = "ORNBTC"
# bought_asset = "DOGEBTC"
# amount = {}
# amount["ORNBTC"] = 735.6
# amount["DOGEBTC"] = 7787


def run(cmd):
    return subprocess.check_output(cmd, shell=True).strip()


def tracker_clock_string():
    msg = ""
    for idx, asset in enumerate(reversed(assets)):
        try:
            output = exchange.fetch_ticker(asset)
            price = output["last"]
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
        clock_title = tracker_clock_string()
        self.title = clock_title


def main():
    app = OrgClockStatusBarApp("starting... ")

    def timer_func(_):
        _str = tracker_clock_string()
        print(_str)  # removing the print statement makes the app hang
        if _str:
            app.title = _str
        else:
            app.title = "Not tracking"

    timer = rumps.Timer(timer_func, interval)
    timer.start()
    app.run()


if __name__ == "__main__":
    main()
