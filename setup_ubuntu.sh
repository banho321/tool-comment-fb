#!/bin/bash
# Setup script for Ubuntu server

echo "=== Facebook Bot Ubuntu Setup ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Install Firefox for headless mode
echo "Installing Firefox..."
sudo apt install -y firefox

# Install Xvfb for virtual display
echo "Installing Xvfb..."
sudo apt install -y xvfb

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install playwright pyyaml flask asyncio

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install firefox
playwright install-deps firefox

# Create necessary directories
echo "Creating directories..."
mkdir -p sessions/acc1
mkdir -p data
mkdir -p logs

# Set permissions
echo "Setting permissions..."
chmod +x continuous_runner.py
chmod +x setup_ubuntu.sh

# Copy systemd service
echo "Setting up systemd service..."
sudo cp facebook-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable facebook-bot

echo "=== Setup Complete ==="
echo "To start the bot: sudo systemctl start facebook-bot"
echo "To check status: sudo systemctl status facebook-bot"
echo "To view logs: sudo journalctl -u facebook-bot -f"
echo "To stop: sudo systemctl stop facebook-bot"
