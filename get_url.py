#!/usr/bin/env python3

import time
from contextlib import closing
from operator import itemgetter

from broker._utils.tools import log
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from ebloc_broker.broker._utils.tools import log

options = Options()
options.add_argument("--disable-extensions")
options.add_argument("--headless")
# options.add_argument("--disable-gpu")
# options.add_argument("--no-sandbox") # linux only
driver = webdriver.Chrome(options=options)

urls = []
names = []
counter = {}
entries = {}


def get_url(url, name):
    """Fetch url information."""
    # use firefox to get page with javascript generated content
    with closing(webdriver.Chrome(options=options)) as browser:
        xcode_path = "//*[@id='__APP']/div/div[2]/div[2]/div[2]/div[2]"
        browser.get(url)
        # button = browser.find_element_by_name('button')
        # button.click()
        # wait for the page to load
        time.sleep(1)
        WebDriverWait(browser, timeout=10).until(lambda x: x.find_elements_by_xpath(xcode_path))
        table = browser.find_element_by_css_selector("div.css-4ndyle")
        data = table.find_element_by_xpath("//*[@id='__APP']/div/div[2]/div[2]/div[2]/div[2]/div/div/div/table").text
        values = data.splitlines()
        names.append(name)

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
            _position = position.replace("BUSD", "USDT")
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
                log(f"{position} => {res} {side}", color="bold green")

                key = f"{_position}_{side}"
                try:
                    counter[key] += 1
                except KeyError:
                    counter[key] = 1

                try:
                    entries[key].append(entry)
                except:
                    entries[key] = [entry]

            else:
                if entry == marked:
                    side = "???"
                elif entry < marked:
                    side = "SHORT"
                elif res[1] > res[2]:
                    side = "LONG"
                log(position + " => " + str(res) + " " + side, "bold red")


def main():
    base_url = "https://www.binance.com/en/futures-activity/leaderboard/user?uid="
    with open("urls.txt") as f:
        urls = [line.rstrip() for line in f]
        for idx, url in enumerate(urls):
            try:
                val = url.split(" ")
                _url = f"{base_url}{val[0]}"
                name = val[1]
                log(f"==> [{idx}] {_url}  {name}")
                get_url(_url, name)
            except Exception as e:
                print(e)

    counter_dict = {}
    counter_x = sorted(counter.items(), key=itemgetter(1), reverse=True)
    for co in counter_x:
        counter_dict[co[0]] = co[1]

    for k, v in counter_dict.items():
        print(f"{k} => {v} {entries[k]}")


if __name__ == "__main__":
    main()
