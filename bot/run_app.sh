#!/bin/bash

RED="\033[1;31m"; GREEN='\033[0;32m'; NC='\033[0m'
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
    echo "warning: `app_async` is already running"
    exit
fi

while true; do
    clear -x
    hypercorn app_async:app -b 0.0.0.0:5000  # --reload
    echo -e "${GREEN}-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-${NC}"
    echo "countdown for 30 seconds  "
    countdown 30
    echo "[  ${GREEN}OK${NC}  ]"
done

# LOG_FILE=trade.log
# nohup hypercorn app_async:app -b 0.0.0.0:5000 >> $LOG_FILE 2>&1 &
# # tail -f $LOG_FILE
