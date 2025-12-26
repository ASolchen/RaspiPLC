#!/usr/bin/env python3

from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO
import mmap
import time
import subprocess
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
app.config["SECRET_KEY"] = "dev"

# ✅ Python 3.13–safe async mode
socketio = SocketIO(app, async_mode="threading")


def read_region(path, length=64):
    """Read first N bytes of a shared memory region."""
    if not Path(path).exists():
        return None

    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        data = mm[:length]
        mm.close()
        return data


def time_emitter():
    while True:
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        ms = int((now % 1) * 1000)

        socketio.emit(
            "time_update",
            {"time": f"{timestamp}.{ms:03d}"}
        )

        # ✅ threading-safe sleep
        time.sleep(0.5)


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
            timeout=10,
        )
        output = result.stdout + result.stderr
    except Exception as e:
        output = str(e)

    return render_template("maintenance.html", output=output)


@socketio.on("connect")
def on_connect():
    print("Client connected")


@socketio.on("disconnect")
def on_disconnect():
    print("Client disconnected")


if __name__ == "__main__":
    socketio.start_background_task(time_emitter)
    socketio.run(app, host="0.0.0.0", port=5000)
