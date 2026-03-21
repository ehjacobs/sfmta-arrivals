#!/bin/bash
set -euo pipefail

echo "=== SF Bus Viewer - Pi Setup ==="

# System dependencies
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev libopenjp2-7

# Enable SPI and I2C
echo "Enabling SPI and I2C..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Project setup
cd /home/pi/sfmta-arrivals

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install "inky[rpi]"

# Systemd service
echo "Installing systemd service..."
sudo cp deploy/sfmta-arrivals.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sfmta-arrivals.service

echo ""
echo "=== Setup complete ==="
echo "1. Copy your config.yaml to /home/pi/sfmta-arrivals/"
echo "2. Start with: sudo systemctl start sfmta-arrivals"
echo "3. Check logs: journalctl -u sfmta-arrivals -f"
