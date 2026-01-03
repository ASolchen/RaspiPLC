#!/bin/bash
set -e

SERVICE="plc-runtime.service"
INSTALL_DIR="/opt/raspiplc/plc-runtime"

echo "[uninstall] Removing plc-runtime..."

systemctl stop "$SERVICE" || true
systemctl disable "$SERVICE" || true

rm -f "/etc/systemd/system/$SERVICE"
rm -rf "$INSTALL_DIR"

systemctl daemon-reload

echo "[uninstall] plc-runtime removed"
