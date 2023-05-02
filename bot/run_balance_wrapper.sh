#!/bin/bash
clear -x
nohup ./run_balance.sh $1 >> "balance_"$1".log" 2>&1 &!  #

# tail -f $fn
