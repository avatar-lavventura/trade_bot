#!/bin/bash

num=$(ps axuww | grep -E "[p]ython3 ./ws.py" | grep -v -e "grep" -e "emacsclient" -e "flycheck_" | wc -l)
if [ $num -ge 1 ]; then
    echo "warning: `python3 ./ws.py` is already running"
    exit
fi

clear
while true
do
    ./ws.py
    echo -e "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
    sleep 30
done
