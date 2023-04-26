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
        echo -ne "#> countdown for 30 seconds\t\t$(date -u --date @$(($_date - `date +%s`)) +%H:%M:%S)\r"
        sleep 0.1
    done
}

check_app () {
    printf "curl https://alpybot.duckdns.org  "
    if curl -sL --fail https://alpybot.duckdns.org -o /dev/null; then
        echo -e "[  ${GREEN}OK${NC}  ]"
    else
        echo -e "[  ${RED}FAIL${NC}  ]"
        exit 1
    fi
}

is_running () {
    ps auxww | grep -E "$1" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l
}

if [ $(is_running "[m]ongodb") -eq 0 ]; then
    echo "warning: mongodb is not running in the background. Do:\n"
    echo "systemctl enable mongod.service\nsudo systemctl start mongod"
    exit
fi

if [ $(is_running "[p]ython3 discord_balance.py $1") -ge 1 ]; then
    echo "warning: discord_balance.py for $1 is already running"
    exit
fi


if [[ $1 == "usdt" ]] ; then
    rm -f /home/alper/.bot/.*.yaml.lock
    echo "rm -f /home/alper/.bot/.*.yaml.lock  done"
fi

clear -x
# check_app
while true; do
    python3 discord_balance.py $1
    echo ""
    countdown 30
    echo "countdown [  OK  ]"
    echo -e "${GREEN}-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-${NC}"
done

# LOG_FILE=_binance_balance.log
# nohup python3 -u binance_balance.py >> $LOG_FILE 2>&1 &
# sleep 1
# tail -f $LOG_FILE
