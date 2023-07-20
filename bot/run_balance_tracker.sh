#!/bin/bash

is_running () {
    ps auxww | grep -E "$1" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l
}

if [ $(is_running "[p]ython3 ./bal.py") -ge 1 ]; then
    echo "warning: ./bal.py is already running"
    tail -f bal.log
else
    echo "++++++++++++++++++++++++++++++++++++++++++++++++" >> bal.log
    nohup ./bal_stats.py >> bal.log 2>&1 &
    tail -f bal.log
fi
