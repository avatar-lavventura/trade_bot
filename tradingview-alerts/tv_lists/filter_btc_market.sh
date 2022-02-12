#!/bin/bash

rm binance_btc_markets.txt
wget -q https://sandwichfinance.blob.core.windows.net/files/binance_btc_markets.txt
gawk -i inplace '!a[$0]++' blacklist_btc.txt
LINES=$(cat blacklist_btc.txt)
for LINE in $LINES
do
    sed -i "/"$LINE"/d" binance_btc_markets.txt
done
echo "symbol,base,quote,name" > ../pairs_btc.csv
./convert_into_csv.py binance_btc_markets.txt >> ../pairs_btc.csv
