#!/bin/bash

time_interval="1m"
sed -i.bak "s/^\(  interval:\ \).*/\1$time_interval/" config/futures.yml
rm -f config/futures.yml.bak
grep '  interval:' config/futures.yml

cp config/futures.yml config.yml
cp add-alerts.js tradingview-alerts-home/node_modules/@alleyway/add-tradingview-alerts-tool/dist/add-alerts.js
./tradingview-alerts-home/atat add-alerts -d 2000
