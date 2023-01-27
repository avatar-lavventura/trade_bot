#!/bin/bash

pkill -f "./tracker.py"
LOG_FILE=~/trade_bot/bot/menubar/output.log
rm -f $LOG_FILE
nohup ./tracker.py > $LOG_FILE &
