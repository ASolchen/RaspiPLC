# RaspiPLC

## Overview

**RaspiPLC** is a modular “soft PLC” architecture designed for Raspberry Pi–class devices, using **Linux shared memory** as the central process image.

The system is intentionally decomposed into small, independent services that all attach to the same shared memory regions. This mirrors how a real PLC CPU, I/O, HMI, and communication modules interact internally — but implemented using standard Linux tools.

The Raspberry Pi is treated as a **disposable runtime target**.  
This GitHub repository is the **authoritative source of truth**.

If the SD card fails, the Pi is reimaged, or the project is paused for months, the design should be recoverable from this repository alone.

---

## Core Design Principles

- **Shared memory is the single source of truth**
- **All persistent state lives in shared memory**
- **Services may be stopped or restarted without losing state**
- **Protocols (Modbus, etc.) are adapters, not dependencies**
- **Internal state is protocol-neutral**
- **Control logic is isolated from UI and protocols**
- **Architecture first, implementation second**

The goal is clarity, robustness, and restart-safety — not cleverness.

---

## High-Level Architecture



                 ┌──────────────┐
                 │   UI (Flask) │
                 └──────┬───────┘
                        │
              ┌─────────▼─────────┐
              │  Shared Memory     │  ← Process Image
              │  (/dev/shm)        │
              └─────────┬─────────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
┌───────▼───────┐ ┌─────▼────────┐ ┌─────▼─────────┐
│ Runtime       │ │ IO Bridge     │ │ Modbus Adapter│
│ (Soft PLC)    │ │ (GPIO/SPI)    │ │ (Optional)    │
└───────────────┘ └────────────────┘ └──────────────┘

Shared memory represents the **process image** of the controller.  
All services attach to it. No service owns it at runtime.

---

## Services (Conceptual)

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

### 2. Runtime (`runtime`)
**Role:** Control logic (Soft PLC)

- Executes the state machine / control logic
- Reads inputs and commands from shared memory
- Writes outputs and internal state to shared memory
- Runs at a fixed or bounded cycle time

This is the **only service allowed to implement control logic**.

---

### 3. IO Bridge (`io-bridge`)
**Role:** Hardware interface

- Maps physical IO (GPIO, SPI, I²C, PWM, ADC, etc.) to shared memory
- Reads output regions → drives hardware
- Reads hardware → writes input regions

This separation allows:
- Hardware simulation
- Headless operation
- Easy hardware replacement or expansion

---

### 4. UI Webserver (`ui-flask`)
**Role:** Human–Machine Interface

- Local touchscreen UI
- Implemented as a Flask web application
- Reads state and parameters from shared memory
- Writes commands and setpoints to shared memory
- Contains **no control logic**

Typically displayed via Chromium in kiosk mode.

---

### 5. Modbus Adapter (`modbus-adapter`) *(Optional)*
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

Internally, memory regions are **named by function**, not by protocol concepts such as coils or registers.

Examples of functional regions (illustrative, not final):

- Inputs (raw sensor values)
- Outputs (actuator commands)
- Internal runtime state
- Commands (from UI or external systems)
- Parameters / setpoints

Protocol-specific mappings (Modbus coils/registers, etc.) happen **only in adapter services**.

---

## Repository Structure

This repository is organized by service.  
Each service is self-contained and may eventually live in its own repository.

RaspiPLC/
├── README.md
├── docs/
│ └── architecture.md
│
├── shm-core/
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
- **Source of truth:** GitHub
- **Deployment:** `git pull` + `install.sh`

The Raspberry Pi is considered **disposable** and may be re-imaged at any time.

All changes should originate from the repository, not be made ad-hoc on the target system.

---

## Project Status

This project is currently in the **architecture and scaffolding phase**.

Primary goals at this stage:
- Lock in naming and boundaries
- Document intent clearly
- Avoid premature coupling
- Ensure the design survives long pauses in development

Working code is explicitly secondary to a recoverable design.

---

## Non-Goals (At Least Initially)

- High availability or redundancy
- Hard real-time guarantees
- Safety certification
- Multi-user authentication systems
- Cloud integration

These may be explored later, but are intentionally out of scope for the initial design.

---

## Why This Exists

This project exists to explore a clean, understandable, and restart-safe way to build a soft PLC using Linux primitives — without burying the design inside a single monolithic service.

If this README still makes sense six months from now, it has done its job.

---

## License

MIT
