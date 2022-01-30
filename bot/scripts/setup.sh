#!/bin/bash

# docker
# ======
mkdir -p ~/docker
cp docker-compose.yml ~/docker
cd ~/docker
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart docker
docker-compose up -d
