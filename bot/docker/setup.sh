#!/bin/bash

mkdir -p ~/docker
cp docker-compose.yml ~/docker
cd ~/docker
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart docker
docker-compose up -d
docker ps

# ports
sudo firewall-cmd --add-port=5000/tcp --permanent --zone=docker
sudo firewall-cmd --reload
sudo firewall-cmd --list-all --zone=docker
sudo ufw allow 5000/tcp
sudo ufw allow 80/tcp
sudo ufw allow 81/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo systemctl enable ufw
sudo ufw status verbose
sudo nmap localhost
