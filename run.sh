#!/usr/bin/env bash
set -e
mkdir -p logs
touch logs/tornado.log
cat /dev/null > logs/tornado.log
cat /dev/null > logs/memory.txt
git pull origin master

# setup ulimit for open file limit
ulimit -Hn 1000000
ulimit -Hs 819200
ulimit -n 819200
ulimit -s 819200

python Main.py

