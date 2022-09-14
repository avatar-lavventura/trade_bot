#!/bin/bash

cp config/bist.yml config.yml
cp add-alerts.js tradingview-alerts-home/node_modules/@alleyway/add-tradingview-alerts-tool/dist/add-alerts.js
./tradingview-alerts-home/atat add-alerts -d 2000
