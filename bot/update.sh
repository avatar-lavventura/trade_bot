#!/bin/bash

current_dir=$(pwd)
cp ~/.bot/*.yaml ~/trade_bot/bot/yaml_files/
cd ~/trade_bot/tradingview-alerts/tv_lists
./filter_usdt_market.sh
./filter_btc_market.sh
cd $current_dir
