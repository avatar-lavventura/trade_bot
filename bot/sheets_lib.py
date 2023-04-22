#!/usr/bin/env python3

import time

import gspread
from broker._utils._log import log


def fetch_withdrawn(sh) -> (float, float, float):
    while True:
        try:
            output_1 = sh.sheet1.get("L2")
            output_2 = sh.sheet1.get("I4:I5")
            return float(output_1[0][0]), float(output_2[0][0]), float(output_2[1][0])
        except Exception as e:
            log(f"Fetching from google sheets... {e}", end="\r")
            time.sleep(2.5)


def main():
    gc = gspread.service_account()
    sh = gc.open("guncel_kendime_olan_borclar")
    print(fetch_withdrawn(sh))


if __name__ == "__main__":
    main()
