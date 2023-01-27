#!/bin/bash

wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_usdt_markets.txt
sed -i '/DOWNUSDT/d' binance_usdt_markets.txt
sed -i '/UPUSDT/d' binance_usdt_markets.txt
gawk -i inplace '!a[$0]++' blacklist_usdt.txt
for LINE in $(cat blacklist_usdt.txt); do
    sed -i "/"$LINE"/d" binance_usdt_markets.txt
done
echo "symbol,base,quote_asset,name" > ../pairs_usdt.csv
./convert_into_csv.py binance_usdt_markets.txt >> ../pairs_usdt.csv


wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_busd_markets.txt
sed -i '/DOWNUSDT/d' binance_busd_markets.txt
sed -i '/UPUSDT/d' binance_busd_markets.txt
# gawk -i inplace '!a[$0]++' blacklist_busd.txt
# for LINE in $(cat blacklist_busd.txt); do
#     sed -i "/"$LINE"/d" binance_busd_markets.txt
# done
# echo "symbol,base,quote_asset,name" > ../pairs_busd.csv
# ./convert_into_csv.py binance_busd_markets.txt >> ../pairs_busd.csv
