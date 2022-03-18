#!/bin/bash

current_dir=$(pwd)
cp ~/.bot/*.yaml ~/trade_bot/bot/yaml_files/
cd ~/trade_bot/tradingview-alerts/tv_lists
cd $current_dir
