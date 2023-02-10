#!/bin/bash

wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_btc_markets.txt
gawk -i inplace '!a[$0]++' blacklist.txt
for LINE in $(cat blacklist.txt); do
    sed -i "/:"$LINE"BTC/d" binance_btc_markets.txt
done
echo "symbol,base,quote_asset,name" > ../pairs_btc.csv
./convert_into_csv.py binance_btc_markets.txt "BTC" >> ../pairs_btc.csv
