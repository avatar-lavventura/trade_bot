#!/usr/bin/env python3

from utils import log

data = (
    "'Symbol Size Entry Price Mark Price\nPNL (ROE %)\nATOMUSDT 118.57000000 5.06 5.39\n39.52 (308.9631%)\nALPHAUSDT"
    " 3,692.00000000 0.19 0.19\n11.76 (82.5906%)\nBATUSDT 2,757.30000000 0.22 0.21\n-10.01 (-84.9682%)\nXLMUSDT"
    " 7,823.00000000 0.15 0.15\n-12.09 (-76.3159%)\nTHETAUSDT 752.90000000 1.45 1.47\n14.85 (67.2786%)\nBELUSDT"
    " 342.00000000 0.88 0.90\n7.57 (123.1072%)\nVETUSDT 1.00000000 0.02 0.02\n0.00 (705.6955%)\nZILUSDT 8,912.00000000"
    " 0.08 0.09\n77.48 (498.3304%)\BTCUSDT 1,048.00000000 0.62 0.62\n4.86 (37.1515%)'"
)


values = data.splitlines()
nV = len(values)
positions = {}

for index in range(2, nV, 2):
    val = values[index]
    chunks = val.split(" ")
    positions[chunks[0]] = [chunks[1], chunks[2], chunks[3], values[index + 1]]

print("Symbol Size Entry Price Mark Price PNL (ROE %)")
for position in positions:
    res = positions[position]
    if float(res[3].split(" ")[0]) > 0:  # profit positions
        if res[2] < res[3]:
            side = "LONG"
        elif res[2] > res[3]:
            side = "SHORT"
        log(position + " => " + str(res) + " " + side, "green")
    else:
        if res[2] < res[3]:
            side = "LONG"
        elif res[2] > res[3]:
            side = "SHORT"

        log(position + " => " + str(res), "red")

# TODO: pull prices from binance
