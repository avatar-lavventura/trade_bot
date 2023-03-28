#!/bin/bash

pkill -f "Python tracker.py"
LOG_FILE=~/trade_bot/bot/menubar/output.log
rm -f $LOG_FILE
nohup ~/venv/bin/python3 tracker.py > $LOG_FILE &
