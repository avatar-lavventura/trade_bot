#!/bin/bash

LOG_FILE=_binance_balance.log
nohup python3 -u binance_balance.py >> $LOG_FILE 2>&1 &
sleep 1
tail -f $LOG_FILE
