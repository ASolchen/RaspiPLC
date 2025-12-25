#!/bin/bash
set -e

SERVICE_NAME="raspiplc-kiosk.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME"
INSTALL_DIR="/opt/raspiplc/hmi-client"

echo "[uninstall] Removing HMI client..."

# Stop and disable kiosk service
if systemctl --user list-unit-files | grep -q "$SERVICE_NAME"; then
    systemctl --user stop "$SERVICE_NAME" || true
    systemctl --user disable "$SERVICE_NAME"
    rm -f "$SERVICE_FILE"
fi

# Reload user systemd
systemctl --user daemon-reexec
systemctl --user daemon-reload

# Remove installed files
rm -rf "$INSTALL_DIR"

# Remove Chromium (handle both possible package names)
if dpkg -l | grep -q '^ii.*chromium-browser'; then
    sudo apt remove -y chromium-browser
elif dpkg -l | grep -q '^ii.*chromium'; then
    sudo apt remove -y chromium
fi

echo "[uninstall] HMI client removed"
echo "[uninstall] NOTE: UI server and shared memory remain untouched"

