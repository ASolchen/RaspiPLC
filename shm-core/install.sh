#!/bin/bash
set -e

SERVICE_NAME="raspiplc-shm-init"
INSTALL_DIR="/opt/raspiplc/shm-core"
SYSTEMD_DIR="/etc/systemd/system"
CONFIG_DIR="/etc/raspiplc"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing shm-core..."

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

REFERENCE_TAGS="$SCRIPT_DIR/../config/tags.json"
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
    echo "WARNING: No reference tags.json found at:"
    echo "  $REFERENCE_TAGS"
    echo "shm-core does not require this file, but other services will."
fi

# ----------------------------------------------------------------------
# Install shm-core files
# ----------------------------------------------------------------------

echo "Installing shm-core files to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

cp "$SCRIPT_DIR/shm_init.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/shm_layout.py" "$INSTALL_DIR/"

chmod 755 "$INSTALL_DIR/shm_init.py"
chmod 644 "$INSTALL_DIR/shm_layout.py"

# ----------------------------------------------------------------------
# Install systemd unit
# ----------------------------------------------------------------------

echo "Installing systemd unit"
cp "$SCRIPT_DIR/raspiplc-shm-init.service" "$SYSTEMD_DIR/"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ----------------------------------------------------------------------
# Run shm-core once immediately
# ----------------------------------------------------------------------

echo "Starting shm-core initialization"
systemctl start "$SERVICE_NAME"

echo "shm-core installation complete."
