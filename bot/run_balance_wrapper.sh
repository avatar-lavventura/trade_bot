#!/bin/bash
fn=$HOME"/.bot/balance_"$1".log"
nohup ./run_balance.sh $1 >> $fn 2>&1 &!  #
# tail -f $fn
