#!/bin/bash

rm binance_usdt_markets.txt
wget -q https://sandwichfinance.blob.core.windows.net/files/binance_usdt_markets.txt
sed -i '/DOWNUSDT/d' binance_usdt_markets.txt
sed -i '/UPUSDT/d' binance_usdt_markets.txt
gawk -i inplace '!a[$0]++' blacklist.txt
for LINE in $(cat blacklist.txt)
do
    sed -i "/"$LINE"/d" binance_usdt_markets.txt
done
echo "symbol,base,quote,name" > ../pairs_usdt.csv
./convert_into_csv.py binance_usdt_markets.txt >> ../pairs_usdt.csv
