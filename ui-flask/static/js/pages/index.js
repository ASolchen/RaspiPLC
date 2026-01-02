/* ---------- Tag updates from backend ---------- */

window.onTagUpdate = function (tags, ts) {
    console.log("Tag update:", tags, ts);
    if (tags["smoker.temp"] !== undefined) {
        document.getElementById("smoker-temp").textContent =
            tags["smoker.temp"].toFixed(1);
    }

    if (tags["meat.temp"] !== undefined) {
        document.getElementById("meat-temp").textContent =
            tags["meat.temp"].toFixed(1);
    }

    if (tags["heater.1.pct"] !== undefined) {
        document.getElementById("heater-pct").textContent =
            tags["heater.1.pct"];
    }
};

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
