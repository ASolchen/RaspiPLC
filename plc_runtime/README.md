# RaspiPLC – PLC Runtime Service

## Overview

The PLC Runtime is a systemd-managed Python service that executes cyclic control logic in a PLC-like fashion.

It is responsible for:
- Running user-defined control logic in a fixed scan loop
- Reading and writing process tags via the RaspiPLC shared-memory backplane (shm-service)
- Acting as the logic engine in the RaspiPLC architecture

The runtime does not manage IO, networking, or shared memory directly. All tag access is performed through the existing shm-service.

---

## Architecture

- **shm-service**
  - Owns shared memory regions
  - Loads tag definitions
  - Exposes tag read/write via IPC

- **plc-runtime**
  - Executes cyclic logic
  - Reads and writes tags
  - Restartable without affecting memory

- **UI / HMI (optional / future)**
  - Observes and manipulates tags

---

## Installation Location

At runtime, the PLC Runtime is installed to:

```
/opt/raspiplc/plc-runtime/
```

Main executable:

```
/opt/raspiplc/plc-runtime/plc_runtime.py
```

This file is the authoritative runtime logic.

---

## Service Control

Start (RUN):

```
sudo systemctl start plc-runtime
```

Stop (HALT):

```
sudo systemctl stop plc-runtime
```

Restart (Reload Logic):

```
sudo systemctl restart plc-runtime
```

Restart stops the current process and starts a new one, reloading all Python code from disk.

---

## Logs and Status

Check service status:

```
sudo systemctl status plc-runtime
```

View recent logs:

```
sudo journalctl -u plc-runtime -n 50
```

Follow logs live:

```
sudo journalctl -u plc-runtime -f
```

---

## Updating Runtime Logic

The PLC runtime always executes code from:

```
/opt/raspiplc/plc-runtime/plc_runtime.py
```

### Option 1 – Edit live (development)

```
sudo nano /opt/raspiplc/plc-runtime/plc_runtime.py
sudo systemctl restart plc-runtime
```

### Option 2 – Edit in repo and reinstall (recommended)

1. Edit `plc_runtime.py` in the git repository
2. Run `install.sh` to copy files into `/opt`
3. Restart the service

Example:

```
sudo ./install.sh
sudo systemctl restart plc-runtime
```

---

## Mental Model

- **Start** = PLC in RUN mode
- **Stop** = PLC in PROGRAM mode
- **Restart** = Program download + RUN

Shared memory and tag values persist across runtime restarts.

---

## Notes

- Editing files in the git repository alone does not affect the running service
- systemd restarts always reload code from `/opt`
- No code is cached between restarts
