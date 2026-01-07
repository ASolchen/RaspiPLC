#!/usr/bin/env bash
set -e

echo "=== RaspiPLC USB IO Bridge Uninstaller ==="

VENV_DIR="$HOME/venvs/raspiplc"
UDEV_RULE="/etc/udev/rules.d/99-raspiplc-usb.rules"

# ---------------- Sanity ----------------

if [[ "$EUID" -eq 0 ]]; then
    echo "ERROR: Do not run this script as root."
    echo "       It will sudo only when needed."
    exit 1
fi

# ---------------- Remove Virtual Environment ----------------

echo "[1/3] Removing Python virtual environment..."

if [[ -d "$VENV_DIR" ]]; then
    rm -rf "$VENV_DIR"
    echo "Removed $VENV_DIR"
else
    echo "Venv not found, skipping"
fi

# ---------------- Remove udev Rule ----------------

echo "[2/3] Removing udev rule..."

if [[ -f "$UDEV_RULE" ]]; then
    sudo rm -f "$UDEV_RULE"
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "Removed udev rule"
else
    echo "udev rule not found, skipping"
fi

# ---------------- Final ----------------

echo "[3/3] Done."
echo
echo "RaspiPLC USB IO Bridge has been removed."
echo "System packages were left intact (by design)."
echo "=============================================="
