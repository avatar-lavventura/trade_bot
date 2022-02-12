#!/bin/bash

RED="\033[1;31m"; GREEN='\033[0;32m'; NC='\033[0m'
if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters provide <usdt or btc>"
    exit 1
fi

if ! [[ $1 == "usdt" || $1 == "btc" ]] ; then
    echo "Illegal argument value should be: 'usdt' or 'btc'"
    exit 1
fi

check_app () {
    printf "curl https://alpyrbot.duckdns.org  [  "
    if curl -sL --fail https://alpyrbot.duckdns.org -o /dev/null; then
        echo -e "${GREEN}OK${NC}  ]"
    else
        echo -e "${RED}FAIL${NC}  ]"
        exit 1
    fi
}

countdown () {  # https://superuser.com/a/611582/723632
   date1=$((`date +%s` + $(expr $1 - 1)))
   while [ "$date1" -ge `date +%s` ]; do
     echo -ne "$(date -u --date @$(($date1 - `date +%s`)) +%H:%M:%S)\r"
     sleep 0.1
   done
}

~/venv/bin/python3 -m pip install -Uq ccxt 2>/dev/null

num=$(ps aux | grep -E "[p]ython3 discord_balance.py $1" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -ge 1 ]; then
    echo "warning: run_balance is already running, count="$num
    exit
fi

clear -x
check_app
while true
do
    python3 discord_balance.py $1
    echo -e "${GREEN}-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-${NC}"
    printf "countdown for 30 seconds "
    countdown 30
    echo "[  ${GREEN}OK${NC}  ]"
done

# LOG_FILE=_binance_balance.log
# nohup python3 -u binance_balance.py >> $LOG_FILE 2>&1 &
# sleep 1
# tail -f $LOG_FILE
