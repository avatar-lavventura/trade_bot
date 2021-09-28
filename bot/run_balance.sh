#!/bin/bash

countdown () {  # https://superuser.com/a/611582/723632
   date1=$((`date +%s` + $(expr $1 - 1)))
   while [ "$date1" -ge `date +%s` ]; do
     echo -ne "$(date -u --date @$(($date1 - `date +%s`)) +%H:%M:%S)\r"
     sleep 0.1
   done
}

while true
do
    python3 binance_balance.py
    echo -e "\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
    countdown 60
done
# LOG_FILE=_binance_balance.log
# nohup python3 -u binance_balance.py >> $LOG_FILE 2>&1 &
# sleep 1
# tail -f $LOG_FILE
