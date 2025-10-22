#!/bin/bash
# Start Facebook Bot on Ubuntu

echo "=== Starting Facebook Bot ==="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please don't run as root. Use a regular user account."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup_ubuntu.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if account session exists
if [ ! -f "sessions/acc1/storage_state.json" ]; then
    echo "Session not found. Please login first:"
    echo "python -m src.login_helper --account acc1"
    exit 1
fi

# Start the bot
echo "Starting continuous runner..."
python continuous_runner.py --account acc1 --interval 30

echo "Bot stopped."
