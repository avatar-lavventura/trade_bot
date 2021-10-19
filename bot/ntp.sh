#!/bin/bash

while true
do
    sudo chronyc makestep &>/dev/null
    chronyc tracking > .tracking.txt
    sleep 15
done
