#!/usr/bin/env python3

import gspread


"""
email=alper-851@citric-yen-197207.iam.gserviceaccount.com
__ https://github.com/burnash/gspread
__ https://docs.gspread.org/en/latest/oauth2.html#enable-api-access
"""


def main():
    gc = gspread.service_account()
    sh = gc.open("guncel_kendime_olan_borclar")
    print(sh.sheet1.get("A1"))
    print(sh.sheet1.get("A2"))
    print(sh.sheet1.get("A3"))
    # sh.sheet1.update("A7", 11)
    # sh.sheet1.update("A8", 12)
    # sh.sheet1.update("A8", 13)
    # Update a range
    # sh.sheet1.update("A24:B24", [[1, 2]])


if __name__ == "__main__":
    main()
