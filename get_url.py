#!/usr/bin/env python3

import time

# mark price is current value
from contextlib import closing
from operator import itemgetter

from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from utils import log

opts = FirefoxOptions()
opts.add_argument("--headless")

urls = []
names = []
counter = dict()  # noqa
entries = dict()  # noqa


def get_url(url):
    log(f"==> {url} ", end="")
    # use firefox to get page with javascript generated content
    with closing(webdriver.Firefox(options=opts)) as browser:
        browser.get(url)
        # button = browser.find_element_by_name('button')
        # button.click()
        # wait for the page to load
        time.sleep(1)
        WebDriverWait(browser, timeout=10).until(
            lambda x: x.find_elements_by_xpath("//*[@id='__APP']/div/div[1]/div[2]/div[2]")
        )

        # store it to string variable
        # page_source = browser.page_source
        table = browser.find_element_by_css_selector("div.css-1afj3g1")
        data = table.find_element_by_xpath("//*[@id='__APP']/div/div[1]/div[2]/div[2]/div[2]/div/div").text
        values = data.splitlines()
        _name = table.find_element_by_xpath("//*[@id='__APP']/div/div[1]/div[2]/div[1]/div[1]/div").text
        log(_name)
        names.append(_name)

    nV = len(values)
    positions = {}

    if nV > 3:
        for index in range(2, nV, 2):
            val = values[index]
            chunks = val.split(" ")
            symbol = chunks[0]
            _pc = (
                str(
                    int(
                        float(
                            values[index + 1]
                            .split(" ")[1]
                            .replace(",", "")
                            .replace("%", "")
                            .replace("(", "")
                            .replace(")", "")
                        )
                    )
                )
                + "%"
            )
            positions[symbol] = [
                chunks[1],
                chunks[2],
                chunks[3],
                round(float(values[index + 1].split(" ")[0].replace(",", ""))),
                _pc,
            ]

        # print("Symbol Size Entry Price Mark Price PNL (ROE %)")
        for position in positions:
            res = positions[position]
            entry = float(res[1].replace(",", ""))
            marked = float(res[2].replace(",", ""))

            if res[3] > 0:  # profit positions
                if entry == marked:
                    side = "???"
                elif entry < marked:
                    side = "LONG"
                elif res[1] > res[2]:
                    side = "SHORT"
                log(f"{position} => {res} {side}", color="green")

                try:
                    counter[f"{position}_{side}"] += 1
                except:
                    counter[f"{position}_{side}"] = 1

                try:
                    entries[f"{position}_{side}"].append(entry)
                except:
                    entries[f"{position}_{side}"] = [entry]

            else:
                if entry == marked:
                    side = "???"
                elif entry < marked:
                    side = "SHORT"
                elif res[1] > res[2]:
                    side = "LONG"
                log(position + " => " + str(res) + " " + side, "red")


with open("urls.txt") as f:
    lines = [line.rstrip() for line in f]

for line in lines:
    urls.append(line)

for idx, url in enumerate(urls):
    try:
        get_url(url)
    except:
        # _colorize_traceback()
        pass

log("=========================================================================", color="blue")
counter_x = sorted(counter.items(), key=itemgetter(1), reverse=True)
counter_dict = {}
for co in counter_x:
    counter_dict[co[0]] = co[1]

for k, v in counter_dict.items():
    print(f"{k} => {v} {entries[k]}")


# print(page_source)
# print(data)
