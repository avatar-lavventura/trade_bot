#!/usr/bin/env python3

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ebloc_broker.broker._utils.tools import get_dt_time

logging.getLogger("apscheduler.executors.default").propagate = False


def tick():
    """Tick time.

    __ https://stackoverflow.com/a/49053648/2402577
    """
    print(f"Tick! The time is: {get_dt_time()}")


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, "cron", minute="*")
    scheduler.start()
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
