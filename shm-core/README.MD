# shm-core

## Purpose

`shm-core` is the **infrastructure backbone** of RaspiPLC.

It is responsible for creating and initializing the **shared memory process image**
that all other services attach to at runtime.

This service defines:
- What shared memory regions exist
- How large each region is
- How regions are named
- How they are initialized

No other service is allowed to create, resize, or redefine shared memory.

---

## Role in the System

`shm-core` acts like the **PLC CPU backplane**.

Once it runs:
- The process image exists
- Memory layout is stable
- Other services may start in any order
- State survives restarts of all other services

`shm-core` is **not** a runtime data service.
It runs once at boot, prepares memory, and exits.

All live access to shared memory after initialization is handled by
`shm-service`.

---

## Configuration Files

### Tag Definitions

Tag definitions are **not owned by `shm-core`**.

They live at the system-level configuration path:

    /etc/raspiplc/tags.json

This file defines:
- Tag names
- Memory regions
- Offsets
- Data types
- Access intent

`shm-core` does **not** read or interpret this file.
It only ensures that shared memory regions exist.

Tag changes do **not** require modifying `shm-core`.

---

## Design Responsibilities

`shm-core` is responsible for:

- Creating shared memory regions under `/dev/shm`
- Defining region names and sizes
- Initializing memory contents
- Establishing a stable, versioned memory layout

It is the **single source of truth** for shared memory existence and sizing.

---

## Non-Responsibilities

`shm-core` must never:

- Define tag schemas
- Interpret memory contents
- Implement control logic
- Provide runtime access to memory
- Enforce read/write policy

Those responsibilities belong to downstream services.

---

## Lifecycle

- Runs as a one-shot systemd service
- Executes during system startup
- Creates and initializes shared memory regions
- Exits once memory is ready

After this point, `shm-core` has no runtime role.

---

## Directory Contents

    shm-core/
    ├── README.md
    ├── install.sh
    ├── uninstall.sh
    ├── shm_layout.py
    ├── shm_init.py
    └── raspiplc-shm-init.service

---

## Status

Implemented and operational.

This service should change rarely.
If it is boring and stable, it is doing its job.
