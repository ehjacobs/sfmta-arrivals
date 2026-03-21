#!/bin/bash
set -euo pipefail

echo "=== SFMTA Arrivals - Pi Setup ==="

# Resolve project directory (parent of deploy/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_USER="$(whoami)"

echo "Project directory: $PROJECT_DIR"
echo "User: $RUN_USER"

# System dependencies
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev libopenjp2-7

# Enable SPI and I2C
echo "Enabling SPI and I2C..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Project setup
cd "$PROJECT_DIR"

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install "inky[rpi]"

# Generate and install systemd service
echo "Installing systemd service..."
cat > /tmp/sfmta-arrivals.service <<EOF
[Unit]
Description=SFMTA Arrivals
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python -m src.main --config config.yaml
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/sfmta-arrivals.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sfmta-arrivals.service

echo ""
echo "=== Setup complete ==="
echo "1. Copy your config.yaml to $PROJECT_DIR/"
echo "2. Start with: sudo systemctl start sfmta-arrivals"
echo "3. Check logs: journalctl -u sfmta-arrivals -f"
