#!/usr/bin/env python3

from flask import Flask, render_template
import mmap
import os

from pathlib import Path
from flask import redirect, url_for
import subprocess
import os

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

@app.route("/maintenance")
def maintenance():
    return render_template("maintenance.html")

@app.route("/update", methods=["POST"])
def update_project():
    repo_dir = "/home/engineer/RaspiPLC"
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout + result.stderr
    except Exception as e:
        output = str(e)

    return render_template(
        "maintenance.html",
        output=output
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

