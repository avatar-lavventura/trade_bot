#!/usr/bin/env python3

import os
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()


"""
date: Use when you want to run the job just once at a certain point of time
interval: Use when you want to run the job at fixed intervals of time
cron: Use when you want to run the job periodically at certain time(s) of day

__ https://stackoverflow.com/a/64270086/2402577
"""


@sched.scheduled_job("cron", hour="12,17")
def job():
    print(f"{datetime.now()}: Hello World!")


try:
    sched.start()
except KeyboardInterrupt:
    print("Program stopped manually!")
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
