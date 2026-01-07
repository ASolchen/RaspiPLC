#!/usr/bin/env bash
set -e

echo "=== RaspiPLC USB IO Bridge Installer ==="

# ---------------- Config ----------------

VENV_DIR="$HOME/venvs/raspiplc"
UDEV_RULE="/etc/udev/rules.d/99-raspiplc-usb.rules"

# Arduino Nano ESP32 VID/PID
USB_VID="2341"
USB_PID="0070"

# ---------------- Sanity Checks ----------------

if [[ "$EUID" -eq 0 ]]; then
    echo "ERROR: Do not run this script as root."
    echo "       It will sudo only when needed."
    exit 1
fi

# ---------------- System Packages ----------------

echo "[1/5] Installing system packages..."

sudo apt update
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    libusb-1.0-0 \
    usbutils

# ---------------- Virtual Environment ----------------

echo "[2/5] Creating Python virtual environment..."

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# ---------------- Python Packages ----------------

echo "[3/5] Installing Python packages..."

pip install --upgrade pip
pip install libusb1 pyserial

# Verify
python - << 'EOF'
import usb1
import serial
print("python-usb1 OK")
print("pyserial OK")
EOF

# ---------------- udev Rule ----------------

echo "[4/5] Installing udev rule..."

RULE_TEXT="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"$USB_VID\", ATTRS{idProduct}==\"$USB_PID\", MODE=\"0666\""

if [[ -f "$UDEV_RULE" ]]; then
    if grep -q "$USB_VID" "$UDEV_RULE"; then
        echo "udev rule already present"
    else
        echo "$RULE_TEXT" | sudo tee -a "$UDEV_RULE" >/dev/null
        echo "Appended udev rule"
    fi
else
    echo "$RULE_TEXT" | sudo tee "$UDEV_RULE" >/dev/null
    echo "Created udev rule"
fi

sudo udevadm control --reload-rules
sudo udevadm trigger

# ---------------- Final Notes ----------------

echo "[5/5] Done."
echo
echo "To use the USB CDC IO bridge:"
echo "  source $VENV_DIR/bin/activate"
echo "  python usb_rgb_poll.py"
echo
echo "You may need to unplug/replug the Nano ESP32 once."
echo "==============================================="
