# shm-core

## Purpose

`shm-core` is the **infrastructure backbone** of RaspiPLC.

It is responsible for creating and initializing the **shared memory process image** that all other services attach to.

This service defines:
- What shared memory exists
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

`shm-core` is not a runtime service.  
It runs once at boot and then exits.

---

## Design Responsibilities

`shm-core` is responsible for:

- Creating shared memory regions under `/dev/shm`
- Defining region names and sizes
- Setting permissions and ownership
- Optionally initializing memory contents (e.g. zeroing)
- Enforcing memory layout version compatibility

---

## Non-Responsibilities

`shm-core` must **never**:

- Contain control or sequencing logic
- Implement protocol behavior (Modbus, etc.)
- Interpret memory contents semantically
- Read or write live process values after initialization
- Depend on any other RaspiPLC service

---

## Design Rules

The following rules are **non-negotiable**:

1. `shm-core` is the *only* component allowed to create shared memory
2. Memory layout is defined in exactly one place
3. Region names are functional and protocol-neutral
4. Memory layout changes require an explicit version bump
5. Other services must fail clearly if expected regions are missing or incompatible

Breaking these rules will introduce tight coupling and undefined behavior.

---

## Shared Memory Philosophy

Shared memory represents the **authoritative process image** of the controller.

All persistent state lives here:
- Inputs
- Outputs
- Internal state
- Commands
- Parameters

If a service restarts, state must still be present.

---

## Lifecycle

- Runs as a **one-shot systemd service**
- Executes during system startup
- Creates and initializes shared memory
- Exits once memory is ready

After this point, `shm-core` has no runtime role.

---

## Expected Directory Contents

This directory will eventually contain:

- `README.md` (this file)
- `install.sh`
- `uninstall.sh`
- `shm_layout.py` (single source of truth for memory layout)
- `shm_init.py` (initializer executable)
- `plc-shm-init.service` (systemd unit)

Only `README.md` is present initially to lock in intent.

---

## Why This Exists

Many soft-PLC designs fail because:
- Protocols implicitly create state
- Memory ownership is unclear
- Restart order matters
- State is lost on service restarts

`shm-core` exists to eliminate those failure modes.

If this service is boring and rarely modified, it is doing its job.

---

## Status

Architecture defined.  
Implementation intentionally deferred.

The next step is to define the memory layout in a protocol-neutral way before writing any code.
