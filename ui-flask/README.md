# ui-flask

## Purpose

`ui-flask` provides a **local human–machine interface** for RaspiPLC.

It is a thin Flask-based web application intended to be displayed on a
local touchscreen (e.g. Chromium in kiosk mode).

The UI:
- Reads shared memory directly
- Displays live process values
- Writes commands and setpoints only
- Contains **no control logic**

If the UI crashes or restarts, system state is unaffected.

---

## Design Rules

- No sequencing or automation
- No timing assumptions
- No protocol awareness
- No ownership of state

The UI is intentionally “dumb”.

---

## Status

Initial skeleton: read-only view of shared memory.
