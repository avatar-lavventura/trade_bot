#!/bin/bash

cd ~/.bot/
watch --color tail -n +1 timestamp_usdt.yaml timestamp_btc.yaml
cd ~/trade_bot/bot
