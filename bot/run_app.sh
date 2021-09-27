#!/bin/bash

while true
do
    hypercorn app_async:app -b 0.0.0.0:5000 # --reload
    echo "\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
    sleep 60
done

# LOG_FILE=trade.log
# nohup hypercorn app_async:app -b 0.0.0.0:5000 >> $LOG_FILE 2>&1 &
# # tail -f $LOG_FILE
