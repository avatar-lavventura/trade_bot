#!/usr/bin/env python3

import psutil
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, _remove

_log.ll.LOG_FILENAME = "cpu.log"


def cpu_percent():
    """Check CPU percent change.

    __ https://stackoverflow.com/a/2468983/2402577
    """
    _remove(_log.ll.LOG_FILENAME)
    while True:
        cpu_avg = psutil.cpu_percent(20)  # psutil.cpu_percent(4)
        if cpu_avg > 20:
            log(f"The CPU usage is: [cyan]{cpu_avg}%[/cyan]    [blue]{_date(_type='hour')}[/blue]")


def main():
    cpu_percent()


if __name__ == "__main__":
    main()
