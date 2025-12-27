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
import socket
from typing import Dict, Any

SOCKET_PATH = "/run/raspiplc-shm.sock"


# ---------------------------------------------------------------------------
# IPC
# ---------------------------------------------------------------------------

def send_request(req: Dict[str, Any]) -> Dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(req).encode())
        data = sock.recv(8192)

    if not data:
        raise RuntimeError("No response from shm-service")

    return json.loads(data.decode())


# ---------------------------------------------------------------------------
# Command Parsing
# ---------------------------------------------------------------------------

def parse_read(args):
    if not args:
        raise ValueError("read requires at least one tag name")
    return {"read": args}


def parse_write(args):
    if not args:
        raise ValueError("write requires key=value pairs")

    values = {}
    for arg in args:
        if "=" not in arg:
            raise ValueError(f"Invalid write argument '{arg}', expected key=value")
        key, val = arg.split("=", 1)
        values[key] = float(val)

    return {"write": values}


def parse_reload(_args):
    return {"reload": True}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Case 1: JSON via stdin
    if not sys.stdin.isatty():
        try:
            req = json.load(sys.stdin)
        except Exception as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}))
            sys.exit(1)

    # Case 2: CLI arguments
    else:
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
                req = parse_read(args)
            elif cmd == "write":
                req = parse_write(args)
            elif cmd == "reload":
                req = parse_reload(args)
            else:
                raise ValueError(f"Unknown command '{cmd}'")
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)

    # Send request
    try:
        resp = send_request(req)
        print(json.dumps(resp, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()

