#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip

echo "Removing old virtual environment (if any)..."
rm -rf venv

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python requirements..."
pip install -r requirements.txt

echo
echo "Install complete."
echo
echo "To run:"
echo "  source venv/bin/activate"
echo "  python usb_rgb_poll.py"
