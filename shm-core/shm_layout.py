"""
Shared Memory Layout Definition for RaspiPLC

This module defines the authoritative shared memory layout.
It contains NO logic and performs NO side effects.

IMPORTANT CONCEPTS
------------------
- These regions express INTENT, not hard security boundaries.
- All shared memory is technically writable at the OS level.
- Write enforcement is performed by protocol adapters
  (UI backend, Modbus adapter, etc.), not by shm-core.

OWNERSHIP MODEL
---------------
- The plc-runtime is the conceptual owner of ALL state.
- External services submit requests and observe state.
"""

# Increment ONLY when layout changes in a non-backward-compatible way
SHM_LAYOUT_VERSION = 3


# Base directory for shared memory regions
SHM_BASE_PATH = "/dev/shm"


# Shared Memory Regions
#
# Region naming reflects INTENT from the perspective of external services.
#
# - read_only:
#     Logically read-only for UI, protocols, and tools.
#     Written by plc-runtime.
#     Contains process state, inputs, outputs, diagnostics.
#
# - read_write:
#     Writable by external services.
#     Interpreted as requests or commands by plc-runtime.
#
# Enforcement of these rules is handled by protocol backends,
# NOT by the shared memory layer itself.

SHM_REGIONS = {
    "read_only": {
        "filename": "raspiplc_read_only",
        "size": 16384,  # 16 KB
        "description": (
            "Logical read-only region containing authoritative PLC state. "
            "Written by plc-runtime. "
            "Observed by UI and external protocols."
        ),
    },

    "read_write": {
        "filename": "raspiplc_read_write",
        "size": 4096,  # 4 KB
        "description": (
            "Read-write region containing control requests and commands. "
            "Written by UI and external services. "
            "Read and applied by plc-runtime."
        ),
    },
}


# Convenience: fully-qualified paths (derived, do not edit)
SHM_REGION_PATHS = {
    name: f"{SHM_BASE_PATH}/{region['filename']}"
    for name, region in SHM_REGIONS.items()
}


# Sanity checks (import-time only, no side effects)
for name, region in SHM_REGIONS.items():
    assert region["size"] > 0, f"Region '{name}' has invalid size"
    assert "/" not in region["filename"], f"Invalid filename for region '{name}'"
