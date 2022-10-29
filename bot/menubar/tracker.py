#!/usr/bin/env python3

# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

import time
import ccxt
import rumps
import subprocess

# rumps.debug_mode(True)
exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})
assets = ["DOGEUSDT", "DOGEBTC", "ORNBTC"]
timer_duration = 2
# sold = "ORNBTC"
# bought = "DOGEBTC"
# amount = {}
# amount["ORNBTC"] = 735.6
# amount["DOGEBTC"] = 7787


def run(cmd):
    return subprocess.check_output(cmd, shell=True).strip()


def tracker_clock_string():
    msg = ""
    for asset in reversed(assets):
        output = exchange.fetch_ticker(asset)
        price_last = output["last"]
        price = "{:.8f}".format(price_last).strip("0")[1:].strip("0")
        if not msg:
            msg = f"{asset} {price}"
        else:
            msg = f"{asset} {price} | {msg}"

    return msg


class OrgClockStatusBarApp(rumps.App):
    @rumps.clicked("Refresh")
    def update_ticker(self, _):
        clock_title = tracker_clock_string()
        self.title = clock_title


def main():
    app = OrgClockStatusBarApp("starting...")

    def timer_func(timer_duration):
        _str = tracker_clock_string()
        print(_str)  # removing the print statement makes the app hang
        if _str:
            app.title = _str
        else:
            app.title = "Not tracking"

        time.sleep(timer_duration)

    timer = rumps.Timer(timer_func, timer_duration)
    timer.start()
    app.run()


if __name__ == "__main__":
    main()
