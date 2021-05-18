#!/bin/bash

# npx @alleyway/create-tradingview-alerts-home
cp add-alerts-browser.js tradingview-alerts-home/node_modules/@alleyway/add-tradingview-alerts-tool/dist/add-alerts.js
./tradingview-alerts-home/atat --delay 1500 add-alerts
