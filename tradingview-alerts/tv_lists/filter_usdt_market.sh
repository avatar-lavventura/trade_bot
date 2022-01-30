#!/bin/bash

rm binance_usdt_markets.txt
wget -q https://sandwichfinance.blob.core.windows.net/files/binance_usdt_markets.txt
sed -i '/DOWNUSDT/d' binance_usdt_markets.txt
sed -i '/UPUSDT/d' binance_usdt_markets.txt
LINES=$(cat blacklist.txt)
for LINE in $LINES
do
    sed -i "/"$LINE"/d" binance_usdt_markets.txt
done
echo "symbol,base,quote,name" > ../pairs_usdt_spot.csv
./convert_into_csv.py >> ../pairs_usdt_spot.csv
