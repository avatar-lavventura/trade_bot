#!/usr/bin/env python3

import time

import ccxt  # noqa: E402
import rumps

# rumps.debug_mode(True)
# __ https://github.com/jaredks/rumps
# __ https://github.com/srid/org-clock-dashboard

exchange = ccxt.binance({"options": {"adustForTimeDifference": True}, "enableRateLimit": True})


def run(cmd):
    import subprocess

    return subprocess.check_output(cmd, shell=True).strip()


def tracker_clock_string():
    output = exchange.fetch_ticker("ORNBTC")
    return "{:.8f}".format(output["last"]).strip("0")[1:].strip("0")


class OrgClockStatusBarApp(rumps.App):
    @rumps.clicked("Refresh")
    def sayhi(self, _):
        clock_title = tracker_clock_string()
        self.title = clock_title


if __name__ == "__main__":
    app = OrgClockStatusBarApp("alpy")

    def timer_func(sender):  # noqa
        s = tracker_clock_string()
        print(s)  # removing the print statement makes the app hang
        if s is not None:
            app.title = s
        else:
            app.title = "Not tracking"

        time.sleep(10)

    timer = rumps.Timer(timer_func, 5)
    timer.start()
    app.run()
