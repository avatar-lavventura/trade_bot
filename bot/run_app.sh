#!/bin/bash

num=$(ps axuww | grep -E "[h]ypercorn app_async:app" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -ge 1 ]; then
    echo "Warning: run_app is already running"
    exit
fi

while true
do
    hypercorn app_async:app -b 0.0.0.0:5000 # --reload
    echo -e "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
    sleep 30
done

# LOG_FILE=trade.log
# nohup hypercorn app_async:app -b 0.0.0.0:5000 >> $LOG_FILE 2>&1 &
# # tail -f $LOG_FILE
