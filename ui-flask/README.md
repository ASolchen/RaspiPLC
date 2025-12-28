# ui-flask

## Purpose

`ui-flask` provides the **local human–machine interface (HMI)** for RaspiPLC.

It is a Flask + Socket.IO web application intended to be displayed on a
local touchscreen (typically Chromium in kiosk mode).

The UI is a **pure client** of the controller runtime:
- It does not own state
- It does not implement control logic
- It does not access shared memory directly

All interaction with controller data is performed **indirectly via `shm-service`**.

If the UI crashes, restarts, or is not running, controller state is unaffected.

---

## Role in the System

`ui-flask` behaves like a traditional PLC HMI panel.

It:
- Subscribes to live tag updates
- Displays process values to the operator
- Writes commands and setpoints
- Provides operator interaction only

It does **not**:
- Execute sequences
- Perform control decisions
- Simulate data
- Cache authoritative state

---

## Architecture

The UI participates in the system as follows:

    Browser (Chromium)
        ↓ Socket.IO
    Flask UI Backend
        ↓ IPC (Unix socket)
    shm-service
        ↓ mmap
    Shared Memory (/dev/shm)

This ensures:
- One authoritative data source
- No duplicated state
- Restart safety
- Clear separation of responsibilities

---

## Data Flow

### Reading Data

- The browser subscribes to tags via Socket.IO
- The Flask backend tracks per-client subscriptions
- At a configurable rate, the backend:
  - Requests current tag values from `shm-service`
  - Emits updates to subscribed clients

Updates are **pull-based**, rate-limited, and per-client.

---

### Writing Data

- The browser emits a `tag_write` event
- The Flask backend forwards the request to `shm-service`
- Shared memory is updated atomically
- Other services immediately observe the change

The UI does not validate business logic — it only forwards requests.

---

## Design Rules

The following rules are intentional and enforced by structure:

- No control or sequencing logic
- No direct `/dev/shm` access
- No protocol awareness (Modbus, GPIO, etc.)
- No assumptions about update timing
- No persistence of state

The UI must remain **stateless and replaceable**.

---

## Directory Structure

    ui-flask/
    ├── README.md
    ├── app.py
    ├── tags/
    │   ├── runtime.py
    │   └── __init__.py
    ├── web/
    │   ├── routes.py
    │   └── templates/
    ├── static/
    └── raspiplc-ui.service

Key files:

- `app.py`
  - Flask application entry point
  - Starts background update loop
  - Registers Socket.IO namespaces

- `tags/runtime.py`
  - Manages client subscriptions
  - Reads and writes tags via `shm-service`
  - Emits live updates

- `raspiplc-ui.service`
  - systemd unit for running the UI as a service

---

## Relationship to Other Services

- Reads and writes **only** through `shm-service`
- Does not depend on `shm-core` directly
- Does not interact with runtime logic or IO bridges
- May be stopped or restarted at any time

The UI is intentionally **optional**.

---

## Status

**Implemented and operational.**

Current capabilities:
- Live tag subscriptions via Socket.IO
- Per-client rate limiting
- Real-time display of shared memory values
- Write-through of commands and setpoints
- No mock or simulated data sources

Future UI features should remain presentation-only.

---

## Why This Exists

In many soft-PLC systems, the UI becomes a second controller.

`ui-flask` exists to explicitly prevent that.

If this service remains simple, boring, and replaceable, it is doing its job.
