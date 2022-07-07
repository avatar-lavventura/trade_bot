#!/bin/bash

CURRENT_DIR=$(pwd)
GIT_TOPLEVEL=$(git rev-parse --show-toplevel)
cp ~/.bot/*.yaml ~/trade_bot/bot/yaml_files/
rm -f ~/trade_bot/bot/yaml_files/status_*.yaml
rm -f ~/trade_bot/bot/yaml_files/risk_usdt.yaml
DIR=~/.bot/history_progress
if [[ -d "$DIR" ]]; then
    cp -a $DIR ~/trade_bot/bot/yaml_files/
fi
cd ~/trade_bot/tradingview-alerts/tv_lists
$GIT_TOPLEVEL/bot/scripts/filter.sh
cd $CURRENT_DIR
printf "pre-commit.sh  [  OK  ]  "
