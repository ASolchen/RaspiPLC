"""
Shared Memory Layout Definition for RaspiPLC

This module defines the authoritative shared memory layout.
It contains NO logic and performs NO side effects.

All services must import this file to discover:
- Region names
- Sizes
- Intended usage
- Layout version

If this file changes in a breaking way, SHM_LAYOUT_VERSION
MUST be incremented.
"""

# Increment ONLY when layout changes in a non-backward-compatible way
SHM_LAYOUT_VERSION = 1


# Base directory for shared memory regions
SHM_BASE_PATH = "/dev/shm"


# Shared Memory Regions
#
# Naming rules:
# - Functional, not protocol-specific
# - Lowercase with underscores
# - No implicit semantics beyond comments
#
# Sizes are in BYTES.
#
# Regions should be generously sized to avoid frequent layout changes.
# Unused space is acceptable.

SHM_REGIONS = {
    # Raw physical inputs (sensors, digital inputs, ADCs, etc.)
    "inputs": {
        "filename": "raspiplc_inputs",
        "size": 4096,
        "description": "Raw physical input values written by IO bridge",
    },

    # Raw physical outputs (actuators, relays, PWM, etc.)
    "outputs": {
        "filename": "raspiplc_outputs",
        "size": 4096,
        "description": "Raw physical output commands written by runtime",
    },

    # Internal runtime state (state machines, timers, counters)
    "state": {
        "filename": "raspiplc_state",
        "size": 8192,
        "description": "Internal runtime state written by runtime",
    },

    # Commands from UI or external systems
    "commands": {
        "filename": "raspiplc_commands",
        "size": 1024,
        "description": "Operator or external commands",
    },

    # Parameters and tunable values (setpoints, configuration)
    "parameters": {
        "filename": "raspiplc_parameters",
        "size": 2048,
        "description": "Tunable parameters and setpoints",
    },
}


# Convenience: fully-qualified paths (derived, do not edit)
SHM_REGION_PATHS = {
    name: f"{SHM_BASE_PATH}/{region['filename']}"
    for name, region in SHM_REGIONS.items()
}


# Sanity checks (import-time, no side effects)
for name, region in SHM_REGIONS.items():
    assert region["size"] > 0, f"Region '{name}' has invalid size"
    assert "/" not in region["filename"], f"Invalid filename for region '{name}'"
