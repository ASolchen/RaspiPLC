# RaspiPLC

## Overview

**RaspiPLC** is a modular “soft PLC” architecture designed for Raspberry Pi–class devices, using **Linux shared memory** as a centralized **process image**, with a dedicated runtime service controlling access to that memory.

The system is intentionally decomposed into small, independent services that interact through **well-defined boundaries** rather than shared logic. This mirrors how a real PLC CPU, I/O, HMI, and communication modules interact internally — but implemented using standard Linux primitives.

The Raspberry Pi is treated as a **disposable runtime target**.  
This Git repository is the **authoritative source of truth**.

If the SD card fails, the Pi is reimaged, or the project is paused for months, the system should be fully recoverable from this repository alone.

---

## Core Design Principles

- Shared memory represents the authoritative process image
- All persistent controller state lives in shared memory
- No service owns shared memory at runtime
- Access to shared memory is centralized and controlled
- Services may be stopped or restarted without losing state
- Protocols (Modbus, UI, etc.) are adapters, not dependencies
- Internal state is protocol-neutral
- Control logic is isolated from UI and protocols
- Architecture first, implementation second

The goal is clarity, robustness, and restart safety — not cleverness.

---

## High-Level Architecture

    Browser / External Clients
                ↓
           UI (Flask)
                ↓ IPC
          shm-service
                ↓ mmap
        Shared Memory (/dev/shm)
                ↓
    ┌──────────────┬──────────────┬──────────────┐
    │              │              │              │
 Runtime       IO Bridge     Modbus Adapter   Other Adapters
 (Soft PLC)    (GPIO/SPI)    (Optional)

Shared memory represents the **process image** of the controller.

All services interact with shared memory **only via `shm-service`**.

---

## Services

Each service is intentionally small, focused, and independently restartable.

### Shared Memory Core (shm-core)

Role: Infrastructure / backplane

- Creates shared memory regions
- Defines region names and sizes
- Initializes memory contents
- Runs once at boot and exits

No other service may create, resize, or redefine shared memory.

---

### Shared Memory Service (shm-service)

Role: Runtime data access authority

- Owns all mmap access to shared memory
- Enforces tag layout, types, and bounds
- Provides IPC-based read/write access
- Supports hot-reload of tag definitions
- Runs continuously

This service acts like the PLC backplane and tag database.

---

### Runtime (Soft PLC)

Role: Control logic execution

- Executes state machines or control logic
- Reads inputs and commands via shm-service
- Writes outputs and internal state via shm-service
- Runs at a bounded or fixed cycle time

This is the only service allowed to implement control logic.

---

### IO Bridge

Role: Hardware abstraction

- Maps physical IO to shared memory
- Reads outputs and drives hardware
- Reads hardware and updates inputs
- Uses shm-service exclusively for access

Allows hardware simulation and replacement without affecting logic.

---

### UI Webserver (ui-flask)

Role: Human–machine interface

- Local touchscreen UI
- Flask + Socket.IO backend
- Subscribes to live tag updates
- Writes commands and setpoints
- Contains no control logic

The UI is optional and replaceable.

---

### Modbus Adapter (Optional)

Role: External protocol adapter

- Maps shared memory to Modbus TCP
- Provides external system access
- Owns no state
- Contains no logic

Protocols are treated like fieldbus cards, not CPUs.

---

## Shared Memory Philosophy

Shared memory represents the **authoritative process image**.

Memory regions are named by function, not protocol concepts.

Typical regions include:

- Inputs
- Outputs
- Internal runtime state
- Commands
- Parameters / setpoints

Protocol-specific mappings happen only in adapter services.

---

## Repository Structure

    RaspiPLC/
    ├── README.md
    ├── docs/
    │   └── architecture.md
    ├── shm-core/
    ├── shm-service/
    ├── runtime/
    ├── io-bridge/
    ├── ui-flask/
    └── modbus-adapter/

Each service directory is self-contained and includes its own README and lifecycle scripts.

---

## Development and Deployment Model

- Development machine: PC
- Target runtime: Raspberry Pi
- Source of truth: Git
- Deployment: git pull plus install scripts

The Raspberry Pi is considered disposable and may be reimaged at any time.

---

## Project Status

The project has progressed from architecture into **working infrastructure**.

Implemented and verified:

- Shared memory creation and persistence
- Centralized shared memory access service
- IPC-based read/write semantics
- Flask UI reading and writing real controller state
- Removal of all mock data sources

Future work focuses on features built on this foundation.

---

## Non-Goals

At least initially, the project does not attempt to provide:

- Hard real-time guarantees
- Safety certification
- High availability or redundancy
- Multi-user authentication
- Cloud integration

These may be explored later but are intentionally out of scope.

---

## Why This Exists

Many soft-PLC systems fail because:

- State ownership is unclear
- Restart order matters
- Protocols implicitly create state
- Memory layout drifts over time

RaspiPLC exists to explore a clean, understandable, and restart-safe alternative using standard Linux primitives.

If this README still makes sense six months from now, it has done its job.

---

## License

MIT
