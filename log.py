#!/usr/bin/env python3

import time
from datetime import datetime
from pathlib import Path

from binance.client import Client
from matplotlib import pyplot

from ebloc_broker.broker._utils._log import log

x_data = []
y_data = []
z_data = []
figure = pyplot.figure()
(line,) = pyplot.plot_date(x_data, y_data, "-")
HOME = Path.home()
_cfg = HOME / ".binance.yaml"
api_key = str(_cfg["b"]["key"])
api_secret = str(_cfg["b"]["secret"])
client = Client(api_key, api_secret)


def update():
    future = client.futures_position_information(symbol="GRTUSDT")
    mark = future[0]["markPrice"]

    x_data.append(datetime.now())
    y_data.append(float(mark))
    z_data.append(10)
    line.set_data(x_data, y_data, z_data)
    figure.gca().relim()
    figure.gca().autoscale_view()
    time.sleep(1)
    return (line,)


if __name__ == "__main__":
    p_temp = 0
    mark_temp = 0
    side = ""
    side_m = ""

    while True:
        future = client.futures_position_information(symbol="GRTUSDT")
        mark = future[0]["markPrice"]
        p = client.futures_order_book(symbol="GRTUSDT")["asks"][0][0]

        if float(p) > float(p_temp):
            side = "LONG_price"
        else:
            side = "SHORT_price"

        if float(p) > float(p_temp):
            side_m = "LONG_mark"
        else:
            side_m = "SHORT_mark"

        p_temp = p
        mark_temp = mark

        if p < mark:
            log(f"{p} < {mark} ", color="yellow", end="")
            log(f"{side} {side_m}")
        else:
            log(f"{p} > {mark} ", color="blue", end="")
            log(f"{side} {side_m}")

        time.sleep(1)

    # p = client.futures_order_book(symbol="GRTUSDT")["asks"][0][0]
    # animation = FuncAnimation(figure, update, interval=200)
    # pyplot.show()
