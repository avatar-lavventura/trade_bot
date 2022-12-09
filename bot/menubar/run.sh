#!/bin/bash

pkill -f python3 python
nohup ./tracker.py > output.log &
