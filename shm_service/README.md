# shm-service

## Purpose

`shm-service` is the **authoritative runtime access service** for RaspiPLC shared memory.

It is the only long-running process allowed to:
- Map shared memory
- Read and write live controller data
- Enforce tag layout, types, and access intent

All other services interact with shared memory indirectly via this service.

---

## Configuration

### Tag Definitions

Tag definitions are loaded from:

    /etc/raspiplc/tags.json

This file is the **authoritative tag schema** for the controller.

It defines:
- Tag names
- Memory regions
- Byte offsets
- Data types
- Access intent (read-only, request, etc.)

`shm-service` enforces this schema at runtime.

Changes to tags are made by editing this file and issuing a reload command.
A service restart is not required.

---

## Runtime Reload

After editing the tag configuration:

    shmctl reload

This causes `shm-service` to:
- Re-read `/etc/raspiplc/tags.json`
- Rebuild tag mappings
- Preserve all current shared memory values

---

## Role in the System

`shm-service` owns **access**, not **state**.

- Shared memory is created by `shm-core`
- State is owned by the PLC runtime
- `shm-service` validates and mediates access

This separation prevents corruption and restart-order coupling.

---

## Directory Contents

    shm-service/
    ├── README.md
    ├── shm_service.py
    ├── shmctl.py
    ├── shm-service.service
    ├── install.sh
    └── uninstall.sh

---

## Status

Implemented and operational.

All reads and writes to shared memory must go through this service.
