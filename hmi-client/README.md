# hmi-client

## Purpose

`hmi-client` installs and manages the **local HMI browser client**
for RaspiPLC.

It is responsible for:
- Installing Chromium
- Launching Chromium in kiosk mode
- Auto-starting the HMI at boot

This module does **not**:
- Host web content
- Implement control logic
- Interact with shared memory
- Depend on Flask internals

It is simply a fullscreen browser pointed at the local UI.

---

## Design Philosophy

The HMI client is treated like a **physical operator panel**:

- It can be installed or removed independently
- It depends on the UI service, but does not own it
- It restarts automatically if it crashes
- It is intentionally boring

---

## Assumptions

- Raspberry Pi OS **with desktop** (X11 or Wayland)
- A local UI available at `http://localhost:5000`
- A single-user system (typical embedded HMI)

---

## Behavior

On boot:
1. System starts
2. Desktop session becomes available
3. Chromium launches in kiosk mode
4. RaspiPLC UI is displayed fullscreen

---

## Removal

Uninstalling `hmi-client`:
- Stops kiosk auto-launch
- Removes Chromium
- Does **not** affect the UI server
- Does **not** affect shared memory or runtime logic

---

## Status

Initial implementation: Chromium kiosk auto-launch
