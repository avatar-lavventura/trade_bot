#!/bin/bash

DIR=~/.bot
if [[ -d $DIR ]]; then
    CURRENT_DIR=$(pwd)
    GIT_TOPLEVEL=$(git rev-parse --show-toplevel)
    #
    cd ~/trade_bot/tradingview-alerts/tv_lists
    $GIT_TOPLEVEL/bot/scripts/filter.sh
    #
    cd $CURRENT_DIR
    printf "update_binance_assets.sh  [  OK  ]  "
fi
