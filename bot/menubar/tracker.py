#!/usr/bin/env python3

import re
import rumps

# rumps.debug_mode(True)
# __ https://github.com/jaredks/rumps
alper = 0


def run(cmd):
    import subprocess

    return subprocess.check_output(cmd, shell=True).strip()


def tracker_clock_string():
    global alper
    alper += 1
    return str(alper)


def tracker_goto_clock():
    pass


class OrgClockStatusBarApp(rumps.App):
    @rumps.clicked("Go to current/recent task")
    def current_task(self, _):
        tracker_goto_clock()

    @rumps.clicked("Refresh")
    def sayhi(self, _):
        clock_title = tracker_clock_string()
        self.title = clock_title


if __name__ == "__main__":
    app = OrgClockStatusBarApp("Org clock")

    def timer_func(sender):  # noqa
        s = tracker_clock_string()
        print(s)  # removing the print statement makes the app hang.
        if s is not None:
            app.title = s
        else:
            app.title = "Not tracking"

    timer = rumps.Timer(timer_func, 5)
    timer.start()
    app.run()
