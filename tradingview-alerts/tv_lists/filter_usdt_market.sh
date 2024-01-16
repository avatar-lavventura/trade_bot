#!/bin/bash

wget -O binance_usdt_markets.txt -Nq https://sandwichfinance.blob.core.windows.net/files/binance_usdt_markets.txt
sed -i '/DOWNUSDT/d' binance_usdt_markets.txt
sed -i '/UPUSDT/d' binance_usdt_markets.txt
gawk -i inplace '!a[$0]++' blacklist.txt
for LINE in $(cat blacklist.txt); do
    sed -i "/:"$LINE"USDT/d" binance_usdt_markets.txt
done
echo "symbol,base,quote_asset,name" > ../pairs_usdt.csv
./convert_into_csv.py binance_usdt_markets.txt "USDT" >> ../pairs_usdt.csv

#
wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_busd_markets.txt
sed -i '/DOWNUSDT/d' binance_busd_markets.txt
sed -i '/UPUSDT/d' binance_busd_markets.txt
gawk -i inplace '!a[$0]++' blacklist.txt
for LINE in $(cat blacklist.txt); do
    sed -i "/:"$LINE"BUSD/d" binance_busd_markets.txt
done
echo "symbol,base,quote_asset,name" > ../pairs_busd.csv
./convert_into_csv.py binance_busd_markets.txt "BUSD" >> ../pairs_busd.csv
