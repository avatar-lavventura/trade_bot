#!/bin/bash

LOG_FILE=~/trade_bot/bot/menubar/output.log
rm -f $LOG_FILE
pkill -f "./tracker.py"
nohup ./tracker.py > $LOG_FILE &
