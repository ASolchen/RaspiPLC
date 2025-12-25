#!/bin/bash

URL="http://localhost:5000"
CHROMIUM_BIN="$(command -v chromium)"

echo "[kiosk] Waiting for UI at $URL..."

# Wait until Flask responds
until curl -sf "$URL" >/dev/null; do
    sleep 1
done

echo "[kiosk] UI available, launching Chromium"

exec "$CHROMIUM_BIN" \
    "$URL" \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0

