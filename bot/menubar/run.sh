#!/bin/bash

rm -f output.log
pkill -f "tracker.py"
nohup ./tracker.py > output.log &
