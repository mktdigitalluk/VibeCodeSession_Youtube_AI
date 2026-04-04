#!/bin/bash
# run.sh — daily cron entry point for VibeCodeSession_Youtube_AI
# python-dotenv (in config.py) loads keys.env automatically — no shell export needed.

set -euo pipefail

cd /home/ubuntu/Documents

/home/ubuntu/Documents/venv/bin/python3 main.py
