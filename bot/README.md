# Guide

- https://github.com/Robswc/tradingview-webhooks-bot
- https://github.com/ccxt/ccxt/tree/master/examples/py
- https://github.com/alleyway/add-tradingview-alerts-tool
- https://sandwich.finance/
- https://discord.com/developers/applications

--------------------------------------------------------------------------------

## Disable log

```
$ e ~/venv/lib/python3.8/site-packages/gevent/pywsgi.py

uncomment:
self.time_finish = time.time()
# self.log_request()
```

- Remove `self.time_finish = time.time()`

--------------------------------------------------------------------------------

- [IP_example](http://IP/webhook)


```
sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 5000
```

https://askubuntu.com/a/1046217/660555

------------------------------------------------------------------

- http://www.duckdns.org  // login using github
- https://nginxproxymanager.com/setup/
- https://ubuntu.com/blog/ubuntu-bionic-using-chrony-to-configure-ntp
