#!/bin/bash
set -e

SERVICE_NAME="raspiplc-kiosk.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME"
INSTALL_DIR="/opt/raspiplc/hmi-client"

echo "[install] Installing HMI client (Chromium kiosk)..."

# Update package index
sudo apt update

# Install Chromium if missing
if ! command -v chromium >/dev/null 2>&1; then
    sudo apt install -y chromium
fi

CHROMIUM_BIN="$(command -v chromium)"
echo "[install] Using Chromium binary: $CHROMIUM_BIN"

# Install kiosk launcher (system-owned path)
sudo mkdir -p "$INSTALL_DIR"
sudo cp kiosk-launch.sh "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/kiosk-launch.sh"

# Ensure user systemd directory exists
mkdir -p "$USER_SYSTEMD_DIR"

# Write user systemd service
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=RaspiPLC Chromium Kiosk
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=/opt/raspiplc/hmi-client/kiosk-launch.sh
Restart=always
RestartSec=3

Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority

[Install]
WantedBy=default.target
EOF

# Reload user systemd
systemctl --user daemon-reexec
systemctl --user daemon-reload

# Enable kiosk service
systemctl --user enable "$SERVICE_NAME"

# Ensure user services start at boot
sudo loginctl enable-linger "$USER"

echo "[install] HMI client installed"
echo "[install] Start kiosk with: systemctl --user start $SERVICE_NAME"
echo "[install] Reboot to verify auto-launch"

