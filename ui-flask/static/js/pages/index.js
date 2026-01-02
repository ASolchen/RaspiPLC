// static/js/pages/index.js
console.log("Index page JS loaded!!");
// Append-only list of handlers
window.tagHandlers = [
  {
    tag: "smoker.temp",
    onUpdate: value => {
      document.getElementById("smoker-temp").textContent =
        Number(value).toFixed(1);
    }
  },
  {
    tag: "meat.temp",
    onUpdate: value => {
      document.getElementById("meat-temp").textContent =
        Number(value).toFixed(1);
    }
  },
  {
    tag: "heater.1.pct",
    onUpdate: value => {
      document.getElementById("heater-pct").textContent =
        Math.round(value);
    }
  }
];

/* ---------- Tag write helpers ---------- */

function tagWrite(tag, value) {
    console.log("tagWrite", tag, value);
    if (!window.TagRuntime || !TagRuntime.socket) {
        console.warn("TagRuntime not ready");
        return;
    }

    TagRuntime.socket.emit(
        "tag_write",
        { tag: tag, value: value },
        function (ack) {
            if (ack && ack.status !== "ok") {
                console.warn("Write failed:", ack);
            }
        }
    );
}

function writeHeaterPct() {
    console.log("Writing heater pct");
    const el = document.getElementById("heater-setpoint");
    const value = parseInt(el.value, 10);

    if (isNaN(value)) {
        alert("Invalid heater value");
        return;
    }

    tagWrite("heater.1.pct", value);
}
