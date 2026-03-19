#!/bin/bash
cd /home/ubuntu/Documents

# carrega env
export $(grep -v '^#' keys.env | xargs)

# executa projeto
/home/ubuntu/Documents/venv/bin/python3 main.py
