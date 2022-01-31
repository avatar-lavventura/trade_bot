#!/bin/bash

rm binance_btc_markets.txt
wget -q https://sandwichfinance.blob.core.windows.net/files/binance_btc_markets.txt
LINES=$(cat blacklist_btc.txt)
for LINE in $LINES
do
    sed -i "/"$LINE"/d" binance_btc_markets.txt
done
# echo "symbol,base,quote,name" > ../pairs_usdt_spot.csv
# ./convert_into_csv.py >> ../pairs_usdt_spot.csv
