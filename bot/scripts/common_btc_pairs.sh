#!/bin/bash

rm -f *_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/binance_btc_markets.txt
sed -i 's/^BINANCE://' binance_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/kucoin_btc_markets.txt
sed -i 's/^KUCOIN://' kucoin_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/huobi_btc_markets.txt
sed -i 's/^HUOBI://' huobi_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/bitfinex_btc_markets.txt
sed -i 's/^BITFINEX://' bitfinex_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/coinbase_btc_markets.txt
sed -i 's/^COINBASE://' coinbase_btc_markets.txt

wget -Nq https://sandwichfinance.blob.core.windows.net/files/poloniex_btc_markets.txt
sed -i 's/^POLONIEX://' poloniex_btc_markets.txt

comm -1 -2 binance_btc_markets.txt kucoin_btc_markets.txt > file1.txt
comm -1 -2 file1.txt huobi_btc_markets.txt > file2.txt
# comm -1 -2 file2.txt coinbase_btc_markets.txt > file3.txt
mv file2.txt final.txt

cp final.txt common
rm *_btc_markets.txt && rm *.txt
mv common _common_btc_markets.txt
less _common_btc_markets.txt
