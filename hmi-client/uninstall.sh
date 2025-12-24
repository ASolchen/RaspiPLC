#!/bin/bash
set -e

SERVICE_NAME="raspiplc-kiosk.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME"

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

# Remove Chromium (optional but intentional)
if command -v chromium-browser >/dev/null 2>&1; then
    sudo apt remove -y chromium-browser
elif command -v chromium >/dev/null 2>&1; then
    sudo apt remove -y chromium
fi

echo "[uninstall] HMI client removed"
echo "[uninstall] NOTE: UI server and shared memory remain untouched"

