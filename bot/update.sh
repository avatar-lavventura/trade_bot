#!/bin/bash

current_dir=$(pwd)
cp ~/.bot/*.yaml ~/trade_bot/bot/yaml_files/
rm ~/trade_bot/bot/yaml_files/status_*.yaml
rm ~/trade_bot/bot/yaml_files/risk_usdt.yaml
cp -a ~/.bot/history_progress ~/trade_bot/bot/yaml_files/
cd ~/trade_bot/tradingview-alerts/tv_lists
cd $current_dir
./filter.sh
# ~/personalize/bin/cleanup.sh >/dev/null 2>&1
