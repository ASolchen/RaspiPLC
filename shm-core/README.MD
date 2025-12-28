# shm-core

## Purpose

`shm-core` is the **infrastructure backbone** of RaspiPLC.

It is responsible for creating and initializing the **shared memory process image** that all other services attach to at runtime.

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

All live access to shared memory after initialization is handled by **`shm-service`**.

---

## Design Responsibilities

`shm-core` is responsible for:

- Creating shared memory regions under `/dev/shm`
- Defining region names and sizes
- Setting permissions and ownership
- Initializing memory contents (typically zeroing)
- Establishing a stable, versioned memory layout

It is the **single source of truth** for shared memory existence and sizing.

---

## Non-Responsibilities

`shm-core` must **never**:

- Contain control or sequencing logic
- Implement protocol behavior (Modbus, UI, etc.)
- Interpret memory contents semantically
- Act as a runtime data access API
- Read or write live process values after initialization
- Depend on any other RaspiPLC service

Any of the above belongs in downstream services.

---

## Design Rules

The following rules are **non-negotiable**:

1. `shm-core` is the *only* component allowed to create shared memory
2. Memory layout is defined in exactly one place
3. Region names are functional and protocol-neutral
4. Memory layout changes require an explicit version bump
5. Other services must fail clearly if expected regions are missing or incompatible

Breaking these rules introduces tight coupling and undefined behavior.

---

## Shared Memory Philosophy

Shared memory represents the **authoritative process image** of the controller.

All persistent controller state lives here:
- Inputs
- Outputs
- Internal runtime state
- Commands
- Parameters / setpoints

If a service restarts, **state must still be present**.

This mirrors the behavior of a real PLC CPU.

---

## Lifecycle

- Runs as a **one-shot systemd service**
- Executes during system startup
- Creates and initializes shared memory regions
- Exits once memory is ready

After this point, `shm-core` has **no runtime role**.

---

## Directory Contents

This directory contains the complete implementation of shared memory initialization:

- `README.md` — this document
- `install.sh` — installation script
- `uninstall.sh` — removal script
- `shm_layout.py` — authoritative shared memory layout definition
- `shm_init.py` — shared memory initializer executable
- `raspiplc-shm-init.service` — systemd unit (one-shot)

The layout and initializer are intentionally simple and stable.

---

## Relationship to `shm-service`

`shm-core` and `shm-service` are deliberately separate:

- `shm-core`:
  - Creates memory
  - Defines layout
  - Exits

- `shm-service`:
  - Owns all `mmap()` access
  - Enforces tag bounds and types
  - Provides IPC-based read/write access
  - Runs continuously

This separation prevents:
- Accidental memory corruption
- Implicit ownership
- Restart-order coupling

---

## Why This Exists

Many soft-PLC designs fail because:
- Protocols implicitly create state
- Memory ownership is unclear
- Restart order matters
- State is lost on service restarts

`shm-core` exists to eliminate those failure modes.

If this service is boring, rarely modified, and rarely thought about, it is doing its job.

---

## Status

**Implemented and in use.**

Shared memory creation, initialization, and persistence are operational and verified.

Future changes should be rare and deliberate, as they affect the foundation of the entire system.
