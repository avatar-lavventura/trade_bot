#!/usr/bin/env python3

import re
import urllib  # the lib that handles the url stuff

import requests  # noqa

LATEST_STRING = (
    "Binance Futures Will Delist and Update the Leverage Margin Tiers of USDⓈ-M 1000LUNCBUSD Perpetual Contract"
)


def _check_url(url, silent=False) -> bool:
    new_alerts_str = ""
    new_alerts = True
    data = urllib.request.urlopen(url)  # it's a file like object and works just like a file
    for line in data:  # files are iterable
        if "Will Delist" in line.decode("utf-8"):
            _line = line.decode("utf-8")
            result = re.search("Delisting(.*)catalogs", _line)
            ralper = result.group(0)  # type: ignore
            d = ralper.split('"title"')
            for myline in d:
                try:
                    rrr = re.search(':"(.*)type', myline)
                    output = rrr.group(0)  # type: ignore
                    output = output.replace(':"', "").replace('","type', "").replace("\\u0026", "").replace("  ", " ")
                    if "2022-" in output:
                        break

                    if LATEST_STRING in output:
                        new_alerts = False
                        if not silent:
                            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

                    if new_alerts:
                        new_alerts_str += output

                    if not silent:
                        print(output)
                except:
                    pass

    if new_alerts_str:
        return True
    else:
        return False


if __name__ == "__main__":
    # watch -n 600 ./delist_log.py
    # url = "https://www.binance.com/en/support/announcement/c-49"
    url = "https://www.binance.com/en/support/announcement/delisting?c=161&navId=161"
    print(f"__ {url}\n")
    output = _check_url(url)
    print(output)
