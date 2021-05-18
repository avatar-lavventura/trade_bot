#!/bin/bash

mkdir -p ~/docker
cp docker-compose.yml ~/docker
cd ~/docker
docker-compose up -d
