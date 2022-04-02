#!/usr/bin/env python3

import psutil
from broker._utils import _log
from broker._utils._log import log
from broker._utils.tools import _date, _remove

_log.ll.LOG_FILENAME = "cpu.log"
_remove(_log.ll.LOG_FILENAME)


def cpu_percent():
    """Check cpu percent changes.

    __ https://stackoverflow.com/a/2468983/2402577
    """
    while True:
        cpu_avg = psutil.cpu_percent(20)  # psutil.cpu_percent(4)
        if cpu_avg > 20:
            log(f"The CPU usage is: [cyan]{cpu_avg}%[/cyan]    [blue]{_date(_type='hour')}[/blue]")


if __name__ == "__main__":
    cpu_percent()
