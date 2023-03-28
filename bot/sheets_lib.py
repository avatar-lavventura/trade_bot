#!/usr/bin/env python3

import time


def fetch_withdrawn(sh) -> float:
    while True:
        try:
            return float(sh.sheet1.get("L2")[0][0])
        except:
            time.sleep(2)
