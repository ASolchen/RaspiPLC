#!/bin/bash
set -e

INSTALL_DIR="/opt/raspiplc/plc-runtime"
SERVICE_FILE="plc-runtime.service"

echo "[install] Installing plc-runtime..."

mkdir -p "$INSTALL_DIR"

cp plc_runtime.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/plc_runtime.py"

cp "$SERVICE_FILE" /etc/systemd/system/

systemctl daemon-reload
systemctl enable plc-runtime.service

echo "[install] plc-runtime installed"
