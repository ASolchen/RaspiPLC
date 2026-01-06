#!/usr/bin/env python3
import signal
import sys

from runtime.main import run

RUNNING = True


def shutdown(signum, frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


def main():
    print("[PLC] Runtime starting")
    run(lambda: RUNNING)
    print("[PLC] Runtime stopped")
    sys.exit(0)


if __name__ == "__main__":
    main()
