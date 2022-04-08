#!/bin/bash

CURRENT_DIR=$(pwd)
cd ~/trade_bot/tradingview-alerts/tv_lists
./filter_btc_market.sh
./filter_usdt_market.sh
cd $CURRENT_DIR
