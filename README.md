# RaspiPLC

## Overview

**RaspiPLC** is a modular “soft PLC” architecture designed for Raspberry Pi–class devices, using **Linux shared memory** as a centralized **process image**, with a dedicated runtime service controlling access to that memory.

The system is intentionally decomposed into small, independent services that interact through **well-defined boundaries** rather than shared logic. This mirrors how a real PLC CPU, I/O, HMI, and communication modules interact internally — but implemented using standard Linux primitives.

The Raspberry Pi is treated as a **disposable runtime target**.  
This Git repository is the **authoritative source of truth**.

If the SD card fails, the Pi is reimaged, or the project is paused for months, the system should be fully recoverable from this repository alone.

---

## Core Design Principles

- **Shared memory represents the authoritative process image**
- **All persistent controller state lives in shared memory**
- **No service owns shared memory at runtime**
- **Access to shared memory is centralized and controlled**
- **Services may be stopped or restarted without losing state**
- **Protocols (Modbus, UI, etc.) are adapters, not dependencies**
- **Internal state is protocol-neutral**
- **Control logic is isolated from UI and protocols**
- **Architecture first, implementation second**

The goal is clarity, robustness, and restart-safety — not cleverness.

---

## High-Level Architecture

             ┌──────────────┐
             │   UI (Flask) │
             └──────┬───────┘
                    │ IPC
          ┌─────────▼─────────┐
          │   SHM Service     │  ← Authoritative access
          │ (shm-service)     │
          └─────────┬─────────┘
                    │ mmap
          ┌─────────▼─────────┐
          │  Shared Memory     │  ← Process Image
          │  (/dev/shm)        │
          └─────────┬─────────┘
                    │
    ┌───────────────┼────────────────┐
    │               │                │

┌───────▼───────┐ ┌─────▼────────┐ ┌─────▼─────────┐
│ Runtime       │ │ IO Bridge    │ │ Modbus Adapter│
│ (Soft PLC)    │ │ (GPIO/SPI)   │ │ (Optional)    │
└───────────────┘ └──────────────┘ └───────────────┘

Shared memory represents the **process image** of the controller.  
All services ultimately interact with this memory, but **only via the SHM service**.

---

## Services (Current)

Each service is intentionally small, focused, and independently restartable.

### 1. Shared Memory Core (`shm-core`)
**Role:** Infrastructure / Backplane

- Creates and sizes shared memory regions
- Defines memory layout, naming, and versioning
- Initializes memory contents
- Runs as a one-shot systemd service at boot

**Design rule:**
> No other service may create, resize, or redefine shared memory.

---

### 2. Shared Memory Service (`shm-service`)
**Role:** Runtime data access authority

- Owns all `mmap()` access to shared memory
- Enforces tag layout, types, and bounds
- Provides IPC-based read/write access
- Supports hot-reload of tag definitions
- Runs continuously as a systemd service

This service acts like the **PLC backplane + tag database**, ensuring that:
- No client corrupts memory
- No service relies on implicit offsets
- Restart order does not matter

---

### 3. Runtime (`runtime`)
**Role:** Control logic (Soft PLC)

- Executes the control logic or state machines
- Reads inputs and commands via `shm-service`
- Writes outputs and internal state via `shm-service`
- Runs at a fixed or bounded cycle time

This is the **only service allowed to implement control logic**.

---

### 4. IO Bridge (`io-bridge`)
**Role:** Hardware interface

- Maps physical IO (GPIO, SPI, I²C, PWM, ADC, etc.) to shared memory
- Reads output regions → drives hardware
- Reads hardware → writes input regions
- Accesses memory exclusively via `shm-service`

This separation allows:
- Hardware simulation
- Headless operation
- Easy hardware replacement or expansion

---

### 5. UI Webserver (`ui-flask`)
**Role:** Human–Machine Interface

- Local touchscreen UI
- Implemented as a Flask + Socket.IO application
- Subscribes to live tag updates
- Writes commands and setpoints
- Contains **no control logic**
- Accesses all state through `shm-service`

Typically displayed via Chromium in kiosk mode.

---

### 6. Modbus Adapter (`modbus-adapter`) *(Optional)*
**Role:** External protocol adapter

- Mirrors shared memory to Modbus TCP
- Provides external access for PLCs, SCADA, or test tools
- Contains no logic
- Owns no state
- May be stopped or omitted entirely

Modbus is treated like a **fieldbus card**, not a CPU dependency.

---

## Shared Memory Philosophy

Shared memory represents the **authoritative process image** of the controller.

Memory regions are **named by function**, not by protocol concepts such as coils or registers.

Examples of functional regions:

- Inputs (raw sensor values)
- Outputs (actuator commands)
- Internal runtime state
- Commands (from UI or external systems)
- Parameters / setpoints

Protocol-specific mappings (Modbus coils/registers, etc.) happen **only in adapter services**.

---

## Repository Structure
RaspiPLC/
├── README.md
├── docs/
│ └── architecture.md
│
├── shm-core/
├── shm-service/
├── runtime/
├── io-bridge/
├── ui-flask/
└── modbus-adapter/

Each service directory is expected to contain:
- `README.md`
- `install.sh`
- `uninstall.sh`
- Source files
- systemd service file (where applicable)

---

## Development & Deployment Model

- **Development machine:** Windows PC
- **Target runtime:** Raspberry Pi
- **Source of truth:** Git
- **Deployment:** `git pull` + `install.sh`

The Raspberry Pi is considered **disposable** and may be re-imaged at any time.

All changes should originate from the repository, not be made ad-hoc on the target system.

---

## Project Status

The project has progressed from architecture into **working infrastructure**.

Currently implemented and verified:
- Shared memory creation and persistence
- Centralized SHM access service
- IPC-based read/write semantics
- Flask UI reading and writing real controller state
- Removal of all mock data sources

Future work focuses on **features built on this foundation**, not further plumbing.

---

## Non-Goals (At Least Initially)

- Hard real-time guarantees
- Safety certification
- High availability or redundancy
- Multi-user authentication
- Cloud integration

These may be explored later, but are intentionally out of scope for the initial design.

---

## Why This Exists

This project exists to explore a clean, understandable, and restart-safe way to build a soft PLC using Linux primitives — without burying the design inside a single monolithic service.

If this README still makes sense six months from now, it has done its job.

---

## License

MIT
