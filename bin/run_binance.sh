#!/bin/bash

killall python python3
rm -f cmd.log

nohup python -u ./binance_track.py > cmd.log &
tail -f cmd.log
