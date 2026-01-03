#!/usr/bin/env python3
import time
import signal

from shmctl import ShmCtrl

RUNNING = True
SCAN_TIME = 0.1  # 100 ms scan


def shutdown(signum, frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


def main():
    shm = ShmCtrl()

    print("[PLC] Runtime started")

    INPUT_TAG = "smoker.temp"
    OUTPUT_TAG = "meat.temp"

    while RUNNING:
        try:
            # Read returns dict {tag: value}
            vals = shm.read([INPUT_TAG])
            inp = vals.get(INPUT_TAG, 0)

            out = inp * 2

            shm.write({OUTPUT_TAG: out})

        except Exception as e:
            print(f"[PLC] Error: {e}")

        time.sleep(SCAN_TIME)

    print("[PLC] Runtime stopped")


if __name__ == "__main__":
    main()
