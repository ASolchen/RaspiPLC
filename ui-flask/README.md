# ui-flask

## Purpose

`ui-flask` provides the **local human–machine interface (HMI)** for RaspiPLC.

It is a Flask and Socket.IO application intended to run on the Raspberry Pi
and be displayed in a browser or kiosk environment.

The UI is a pure client of the controller backend.

---

## Tag Usage

The UI does not define or own tag layouts.

All tag definitions originate from:

    /etc/raspiplc/tags.json

The UI:
- Refers to tags by name only
- Does not know offsets or memory regions
- Does not read configuration files directly

All tag reads and writes occur via `shm-service`.

---

## Data Flow

    Browser
        ↓ Socket.IO
    Flask backend
        ↓ IPC
    shm-service
        ↓ mmap
    Shared memory

The UI observes state and submits requests.
It does not own or interpret controller logic.

---

## Design Rules

- No control logic
- No direct shared memory access
- No tag schema definitions
- No persistent state

If the UI stops, restarts, or crashes, controller state is unaffected.

---

## Status

Implemented and operational.

The UI reflects real controller state and writes requests through the
shared memory access service.
