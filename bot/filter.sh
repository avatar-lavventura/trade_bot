#!/bin/bash

current_dir=$(pwd)
cd ~/trade_bot/tradingview-alerts/tv_lists
./filter_usdt_market.sh
./filter_btc_market.sh
cd $current_dir
