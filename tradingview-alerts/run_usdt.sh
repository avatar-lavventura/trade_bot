#!/bin/bash

cd $HOME/trade_bot
git reset --hard HEAD && git pull -r -v
cd $HOME/trade_bot/tradingview-alerts
cp config/usdt_spot.yml config.yml
cp add-alerts.js tradingview-alerts-home/node_modules/@alleyway/add-tradingview-alerts-tool/dist/add-alerts.js
./tradingview-alerts-home/atat --delay 2100 add-alerts
