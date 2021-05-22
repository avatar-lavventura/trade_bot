#!/bin/bash

# https://currentmillis.com
# sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"
# sudo ntpdate -vu time.apple.com
sudo sntp -sS pool.ntp.org  # Force-syncing time helped
sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 5000
