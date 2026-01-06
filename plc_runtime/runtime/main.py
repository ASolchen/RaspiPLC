import time
from shmctrl import ShmCtrl

SCAN_TIME = 0.1


def run(is_running):
    shm = ShmCtrl()

    while is_running():
        cycle(shm)
        time.sleep(SCAN_TIME)


def cycle(shm):
    # placeholder logic
    vals = shm.read(["smoker.temp"])
    temp = vals.get("smoker.temp", 0.0)

    shm.write({
        "meat.temp": temp * 2.0
    })
