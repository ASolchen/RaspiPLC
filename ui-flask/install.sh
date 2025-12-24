#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
INSTALL_DIR="/opt/raspiplc/ui-flask"
SYSTEMD_DIR="/etc/systemd/system"

echo "[install] Installing ui-flask..."

mkdir -p "$INSTALL_DIR"

cp app.py "$INSTALL_DIR/"
cp -r templates static "$INSTALL_DIR/"

cp "$SERVICE_NAME" "$SYSTEMD_DIR/"

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[install] ui-flask installed"
echo "[install] Start with: systemctl start $SERVICE_NAME"
