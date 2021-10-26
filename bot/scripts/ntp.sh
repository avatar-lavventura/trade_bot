#!/bin/bash

while true
do
    sudo chronyc makestep &>/dev/null
    chronyc tracking > .tracking.txt
    sleep 20
done
