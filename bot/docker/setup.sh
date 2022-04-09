#!/bin/bash

mkdir -p ~/docker
cp docker-compose.yml ~/docker
cd ~/docker
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart docker
docker-compose up -d
docker ps

# ports
sudo systemctl enable ufw && sudo ufw enable
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo ufw allow 81/tcp
sudo ufw allow 443/tcp
sudo ufw allow 4001/tcp
sudo ufw allow 5000/tcp
sudo ufw status verbose
sudo nmap localhost
