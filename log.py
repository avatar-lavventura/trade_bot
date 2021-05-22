#!/usr/bin/env python3

import os
import time
from datetime import datetime
from pathlib import Path

from binance.client import Client
from matplotlib import pyplot
<<<<<<< HEAD
from bot.tools import log
||||||| parent of db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)
from matplotlib.animation import FuncAnimation

from utils import log, utc_to_local
=======
>>>>>>> db205bf (Performance from 03.01 => 731% ALL | 518% Long , 213% Short)

HOME = str(Path.home())

x_data, y_data, z_data = [], [], []

figure = pyplot.figure()
(line,) = pyplot.plot_date(x_data, y_data, "-")

_file = f"{HOME}/.binance.txt"
if not os.path.exists(_file):
    with open(_file, "w"):
        pass

# Using readlines()
file1 = open(_file, "r")

Lines = file1.readlines()
api_key = str(Lines[0].strip())
api_secret = str(Lines[1].strip())
client = Client(api_key, api_secret)


def update(frame):
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
