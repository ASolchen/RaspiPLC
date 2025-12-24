#!/bin/bash
set -e

SERVICE_NAME="raspiplc-kiosk.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME"

echo "[install] Installing HMI client (Chromium kiosk)..."

# Ensure system is up to date
sudo apt update

# Install Chromium if missing
if ! command -v chromium-browser >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
    sudo apt install -y chromium-browser || sudo apt install -y chromium
fi

# Ensure systemd user directory exists
mkdir -p "$USER_SYSTEMD_DIR"

# Create kiosk service
cat > "$SERVICE_FILE" <<'EOF'
[Unit]
Description=RaspiPLC Chromium Kiosk
After=network.target raspiplc-ui.service
Requires=raspiplc-ui.service

[Service]
Type=simple
ExecStart=/usr/bin/chromium-browser \
    http://localhost:5000 \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0

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
echo "[install] Reboot to test full auto-launch"
