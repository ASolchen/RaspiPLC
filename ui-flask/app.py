#!/usr/bin/env python3

from flask import Flask, render_template
import mmap
import os

from pathlib import Path

# Hard-coded for now; later imported from shm_layout
SHM_FILES = {
    "inputs": "/dev/shm/raspiplc_inputs",
    "outputs": "/dev/shm/raspiplc_outputs",
    "state": "/dev/shm/raspiplc_state",
    "commands": "/dev/shm/raspiplc_commands",
    "parameters": "/dev/shm/raspiplc_parameters",
}

app = Flask(__name__)


def read_region(path, length=64):
    """Read first N bytes of a shared memory region."""
    if not Path(path).exists():
        return None

    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        data = mm[:length]
        mm.close()
        return data


@app.route("/")
def index():
    regions = {}

    for name, path in SHM_FILES.items():
        data = read_region(path)
        if data is None:
            regions[name] = "(missing)"
        else:
            regions[name] = data.hex(" ")

    return render_template("index.html", regions=regions)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

