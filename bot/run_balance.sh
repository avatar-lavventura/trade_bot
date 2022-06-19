#!/bin/bash

RED="\033[1;31m"; GREEN='\033[0;32m'; NC='\033[0m';
if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters provide <usdt or btc>"
    exit 1
fi

if ! [[ $1 == "usdt" || $1 == "btc" ]] ; then
    echo "Illegal argument value should be: 'usdt' or 'btc'"
    exit 1
fi

countdown () {  # https://superuser.com/a/611582/723632
    _date=$((`date +%s` + $(expr $1 - 1)))
    while [ "$_date" -ge `date +%s` ]; do
        echo -ne "$(date -u --date @$(($_date - `date +%s`)) +%H:%M:%S)                                             \r"
        sleep 0.1
    done
}

check_app () {
    printf "curl https://alpybot.duckdns.org  [  "
    if curl -sL --fail https://alpybot.duckdns.org -o /dev/null; then
        echo -e "${GREEN}OK${NC}  ]"
    else
        echo -e "${RED}FAIL${NC}  ]"
        exit 1
    fi
}

num=$(ps aux | grep -E "[m]ongodb" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -eq 0 ]; then
    echo "warning: mongodb is not running please do:\n"
    echo "systemctl enable mongod.service\nsudo systemctl start mongod"
    exit
fi

num=$(ps aux | grep -E "[p]ython3 discord_balance.py $1" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -ge 1 ]; then
    echo "warning: `discord_balance.py` is already running, count="$num
    exit
fi

clear -x
# check_app
while true
do
    python3 discord_balance.py $1
    echo -e "${GREEN}-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-${NC}"
    printf "countdown for 30 seconds                                                         "
    countdown 30
    echo "[  OK  ]                                                                           "
done

# LOG_FILE=_binance_balance.log
# nohup python3 -u binance_balance.py >> $LOG_FILE 2>&1 &
# sleep 1
# tail -f $LOG_FILE
