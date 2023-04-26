#!/bin/bash

RED="\033[1;31m"; GREEN="\033[0;32m"; NC="\033[0m"

countdown () {  # https://superuser.com/a/611582/723632
    _date=$((`date +%s` + $(expr $1 - 1)))
    while [ "$_date" -ge `date +%s` ]; do
        echo -ne "#> countdown for 30 seconds\t\t$(date -u --date @$(($_date - `date +%s`)) +%H:%M:%S)\r"
        sleep 0.1
    done
}

is_running () {
    ps auxww | grep -E "$1" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l
}

if [ $(is_running "[m]ongodb") -eq 0 ]; then
    echo "warning: mongodb is not running in the background. Do:\n"
    echo "systemctl enable mongod.service\nsudo systemctl start mongod"
    exit
fi

if [ $(is_running "[h]ypercorn app_async:app") -ge 1 ]; then
    echo "warning: app_async is already running"
    exit
fi

while true; do
    # clear -x
    hypercorn app_async:app -b 0.0.0.0:5000  # --reload
    echo ""
    countdown 30
    echo "countdown [  OK  ]"
    echo -e "${GREEN}-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-${NC}"
done

# LOG_FILE=trade.log
# nohup hypercorn app_async:app -b 0.0.0.0:5000 >> $LOG_FILE 2>&1 &
# # tail -f $LOG_FILE
