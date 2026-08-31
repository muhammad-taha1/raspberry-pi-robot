#!/usr/bin/env bash
# Run on the Pi: pulls latest, restarts robotd, tails the log.
set -e

cd "$(dirname "$0")/.."

git pull
sudo systemctl restart robotd
journalctl -fu robotd
