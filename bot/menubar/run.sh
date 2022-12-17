#!/bin/bash

rm -f output.log
pkill -f python python3
nohup ./tracker.py > output.log &
