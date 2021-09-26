# Guide

- https://github.com/ccxt/ccxt/tree/master/examples/py
- https://sandwich.finance/
- https://discord.com/developers/applications
- [swap space](https://www.digitalocean.com/community/tutorials/how-to-add-swap-space-on-ubuntu-20-04)
--------------------------------------------------------------------------------
# [Nginx setup](http://alpyr.duckdns.org:81/)
```
admin@example.com
changeme
```
--------------------------------------------------------------------------------
```
sudo ufw allow 80
sudo ufw allow 81
sudo ufw allow 443

$ sudo ufw enable
$ systemctl enable ufw
$ sudo ufw status
Status: active

To                         Action      From
--                         ------      ----
8080                       ALLOW       Anywhere
80                         ALLOW       Anywhere
443                        ALLOW       Anywhere
81                         ALLOW       Anywhere
5000                       ALLOW       Anywhere
8080 (v6)                  ALLOW       Anywhere (v6)
80 (v6)                    ALLOW       Anywhere (v6)
443 (v6)                   ALLOW       Anywhere (v6)
81 (v6)                    ALLOW       Anywhere (v6)
5000 (v6)                  ALLOW       Anywhere (v6)
```

# Nginx Full Setup Instructions

```cp docker ~/docker```

```
sudo curl -L "https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo systemctl start docker.service

sudo ufw status
sudo chown jenkins:docker /var/run/docker.sock
docker-compose up -d
```

- [IP_example](http://IP/webhook)

https://askubuntu.com/a/1046217/660555

------------------------------------------------------------------

- http://www.duckdns.org  // login using github
- https://nginxproxymanager.com/setup/
- https://ubuntu.com/blog/ubuntu-bionic-using-chrony-to-configure-ntp

# localhost

```
curl -v localhost:5000
curl -X POST http://localhost:5000/webhook -d "DOGEUSDTPERP,buy,enter,1.943,"
```

# public

```
curl https://alpyr-bot.duckdns.org
curl -X POST https://alpyr-bot.duckdns.org/webhook -d "DOGEUSDTPERP,buy,enter,1.943,"
```

# Port-Forwarding, not required
```
sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 5000
```

-----------------

# Tradingview alerts some links

- [Binance Minimum Trading Rules](https://liquidation.atsutane.net/calc)
- [puppeteer google browser](https://github.com/puppeteer/puppeteer)
- [fake gmail address generator and inbox](https://maildim.com/)
- TV_username_last_used => `roxanroxanroxan_5` // ends at Oct 28, 2021


# Git Push:

```
# https://github.com/newren/git-filter-repo#how-do-i-install-it
git filter-repo --invert-paths --path '.DS_Store' --use-base-name
git remote add origin https://github.com/avatar-lavventura/trade_bot.git
git push --set-upstream origin dev -f
```
