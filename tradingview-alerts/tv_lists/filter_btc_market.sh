#!/bin/bash

wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_btc_markets.txt
gawk -i inplace '!a[$0]++' blacklist_btc.txt
for LINE in $(cat blacklist_btc.txt); do
    sed -i "/"$LINE"/d" binance_btc_markets.txt
done
echo "symbol,base,quote_asset,name" > ../pairs_btc.csv
./convert_into_csv.py binance_btc_markets.txt >> ../pairs_btc.csv
