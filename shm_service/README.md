# shm-service

## Purpose

`shm-service` is the **authoritative runtime access service** for RaspiPLC shared memory.

It is the *only* long-running process allowed to:
- `mmap()` shared memory regions
- Read and write live controller state
- Enforce tag layout, types, and bounds

All other services (UI, runtime logic, IO bridge, protocol adapters) interact with shared memory **indirectly via this service**.

This prevents memory corruption, implicit coupling, and restart-order bugs.

---

## Role in the System

`shm-service` acts like the **PLC backplane + tag database**.

Once running:
- Shared memory is safely accessible
- Clients may read or write tags by name
- Tag offsets and types are enforced centrally
- Services may restart without losing state

`shm-service` owns *access*, not *state*.

---

## IPC Interface

`shm-service` exposes a **Unix domain socket** for local IPC.

- Socket path: `/run/raspiplc-shm.sock`
- Transport: Unix stream socket
- Payload format: JSON
- Request/response model

---

## Supported Commands

### Read

Read one or more tags by name.

Request:

    { "read": ["smoker.temp", "meat.temp"] }

Response:

    {
      "read": {
        "smoker.temp": 212.5,
        "meat.temp": 145.0
      }
    }

---

### Write

Write one or more tags atomically.

Request:

    {
      "write": {
        "heater.1.pct": 45
      }
    }

Response:

    { "status": "ok" }

---

### Reload

Reload tag definitions without restarting the service.

Request:

    { "reload": true }

Response:

    { "status": "reloaded" }

---

## Tag Definition File

Tag metadata is defined in a JSON file, typically:

    /etc/raspiplc/tags.json

Example:

    {
      "smoker.temp": {
        "region": "inputs",
        "offset": 0,
        "type": "float32"
      }
    }

---

## Directory Contents

    shm-service/
    ├── README.md
    ├── shm_service.py
    ├── shmctl.py
    ├── tags.example.json
    ├── shm-service.service
    ├── install.sh
    └── uninstall.sh

---

## Status

**Implemented and operational.**

This service forms the foundation for all higher-level features.
