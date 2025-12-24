#!/usr/bin/env python3
"""
Shared Memory Initializer for RaspiPLC

This script creates and initializes the shared memory regions defined
in shm_layout.py. It is intended to run as a one-shot service at boot.

Design rules:
- Imports shm_layout as the single source of truth
- Creates shared memory regions if missing
- Verifies region sizes if already present
- Does NOT interpret or modify live process data
- Safe to run multiple times
"""

import os
import sys
import mmap
from pathlib import Path

from shm_layout import (
    SHM_LAYOUT_VERSION,
    SHM_REGIONS,
    SHM_REGION_PATHS,
)


def ensure_region(name: str, path: str, size: int):
    """
    Ensure a shared memory region exists with the correct size.
    """
    shm_path = Path(path)

    if shm_path.exists():
        actual_size = shm_path.stat().st_size
        if actual_size != size:
            raise RuntimeError(
                f"Shared memory region '{name}' exists but size mismatch: "
                f"{actual_size} != {size}"
            )
        return False  # existed already

    # Create and size the shared memory file
    with open(shm_path, "wb") as f:
        f.truncate(size)

    # Explicitly zero memory (defensive, even though truncate should)
    with open(shm_path, "r+b") as f:
        mm = mmap.mmap(f.fileno(), size)
        mm.write(b"\x00" * size)
        mm.flush()
        mm.close()

    # Set permissions: rw for owner and group
    os.chmod(shm_path, 0o660)

    return True  # created


def main():
    created_any = False

    for name, region in SHM_REGIONS.items():
        path = SHM_REGION_PATHS[name]
        size = region["size"]

        try:
            created = ensure_region(name, path, size)
            if created:
                print(f"[shm-init] Created region '{name}' ({size} bytes)")
                created_any = True
            else:
                print(f"[shm-init] Region '{name}' already exists")
        except Exception as e:
            print(f"[shm-init] ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    if created_any:
        print(f"[shm-init] Shared memory layout initialized (version {SHM_LAYOUT_VERSION})")
    else:
        print(f"[shm-init] Shared memory layout already present (version {SHM_LAYOUT_VERSION})")


if __name__ == "__main__":
    main()
