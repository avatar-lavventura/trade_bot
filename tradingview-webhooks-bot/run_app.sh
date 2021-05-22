#!/bin/bash

LOG_FILE=/home/alper_alimoglu_research2/.eBlocBroker/provider.log
nohup python3 -u app.py >> $LOG_FILE 2>&1 &
sleep 1
tail -f $LOG_FILE
