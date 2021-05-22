#!/bin/bash

LOG_FILE=trade.log
nohup python3 -u app.py >> $LOG_FILE 2>&1 &
sleep 1
tail -f $LOG_FILE
