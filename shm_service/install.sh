#!/bin/bash
set -e

SERVICE_NAME="shm-service"
INSTALL_DIR="/opt/raspiplc/shm-service"
SYSTEMD_DIR="/etc/systemd/system"
CONFIG_DIR="/etc/raspiplc"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing shm-service..."

# ----------------------------------------------------------------------
# Create system configuration directory
# ----------------------------------------------------------------------

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Creating $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
    chmod 755 "$CONFIG_DIR"
fi

# ----------------------------------------------------------------------
# Install reference tags.json (only if missing)
# ----------------------------------------------------------------------

REFERENCE_TAGS="$SCRIPT_DIR/tags.json"
TARGET_TAGS="$CONFIG_DIR/tags.json"

if [ -f "$REFERENCE_TAGS" ]; then
    if [ ! -f "$TARGET_TAGS" ]; then
        echo "Installing reference tags.json to $TARGET_TAGS"
        cp "$REFERENCE_TAGS" "$TARGET_TAGS"
        chmod 644 "$TARGET_TAGS"
    else
        echo "tags.json already exists at $TARGET_TAGS"
        echo "Leaving existing configuration untouched"
    fi
else
    echo "WARNING: No reference tags.json found in shm-service directory"
fi

# ----------------------------------------------------------------------
# Install service files
# ----------------------------------------------------------------------

echo "Installing shm-service files to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

cp "$SCRIPT_DIR/shm_service.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/shmctl.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/shmctrl.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/tags.json" "$INSTALL_DIR/"

chmod 755 "$INSTALL_DIR/shm_service.py"
chmod 755 "$INSTALL_DIR/shmctl.py"
chmod 644 "$INSTALL_DIR/shmctrl.py"
chmod 644 "$INSTALL_DIR/tags.json"

# ----------------------------------------------------------------------
# Install systemd unit
# ----------------------------------------------------------------------

echo "Installing systemd unit"
cp "$SCRIPT_DIR/shm-service.service" "$SYSTEMD_DIR/"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "shm-service installation complete."
