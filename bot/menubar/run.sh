#!/bin/bash

pkill -f python python3
nohup ./tracker.py > output.log &
