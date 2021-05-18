#!/bin/bash

nohup ./app.py > app.log 2>&1 &
tail -f app.log
