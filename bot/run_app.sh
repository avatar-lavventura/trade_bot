#!/bin/bash

countdown () {  # https://superuser.com/a/611582/723632
   date1=$((`date +%s` + $(expr $1 - 1)))
   while [ "$date1" -ge `date +%s` ]; do
     echo -ne "$(date -u --date @$(($date1 - `date +%s`)) +%H:%M:%S)\r"
     sleep 0.1
   done
}

num=$(ps axuww | grep -E "[h]ypercorn app_async:app" | \
          grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -ge 1 ]; then
    echo "Warning: run_app is already running"
    exit
fi

while true
do
    hypercorn app_async:app -b 0.0.0.0:5000 # --reload
    echo -e "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
    echo "countdown for 30 seconds"
    countdown 30 && echo "[  OK  ]"
done

# LOG_FILE=trade.log
# nohup hypercorn app_async:app -b 0.0.0.0:5000 >> $LOG_FILE 2>&1 &
# # tail -f $LOG_FILE
