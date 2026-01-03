#!/usr/bin/env python3
"""
shmctl - CLI client for RaspiPLC shared memory service

This tool:
- Connects to shm-service over IPC
- Sends a single request
- Prints the response
- Exits

It does NOT:
- mmap shared memory
- Know offsets
- Know region sizes
"""

import sys
import json
from typing import Dict, Any

# Import the reusable client
from shmctrl import ShmCtrl


# ---------------------------------------------------------------------------
# Command Parsing
# ---------------------------------------------------------------------------

def parse_read(args):
    if not args:
        raise ValueError("read requires at least one tag name")
    return args


def parse_write(args):
    if not args:
        raise ValueError("write requires key=value pairs")

    values = {}
    for arg in args:
        if "=" not in arg:
            raise ValueError(f"Invalid write argument '{arg}', expected key=value")
        key, val = arg.split("=", 1)

        # Keep your current behavior: parse numbers as float
        # (service will pack based on tag type)
        values[key] = float(val)

    return values


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ctrl = ShmCtrl()

    # Case 1: JSON via stdin
    if not sys.stdin.isatty():
        try:
            req = json.load(sys.stdin)
        except Exception as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}))
            sys.exit(1)

        try:
            # allow raw passthrough
            # e.g. echo '{"read":["tag1"]}' | shmctl
            # or   echo '{"write":{"tag1":1}}' | shmctl
            if "read" in req:
                resp = ctrl._send({"read": req["read"]})
            elif "write" in req:
                resp = ctrl._send({"write": req["write"]})
            elif "reload" in req:
                resp = ctrl._send({"reload": True})
            else:
                resp = ctrl._send(req)

            print(json.dumps(resp, indent=2))
            return

        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)

    # Case 2: CLI arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  shmctl read <tag> [tag ...]")
        print("  shmctl write <tag=value> [tag=value ...]")
        print("  shmctl reload")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == "read":
            tags = parse_read(args)
            resp = {"read": ctrl.read(tags)}

        elif cmd == "write":
            values = parse_write(args)
            resp = ctrl.write(values)

        elif cmd == "reload":
            resp = ctrl.reload()

        else:
            raise ValueError(f"Unknown command '{cmd}'")

        print(json.dumps(resp, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
