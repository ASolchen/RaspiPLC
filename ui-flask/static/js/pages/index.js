// static/js/pages/index.js
console.log("Index page JS loaded (TempCtrl)");

// ---------------------------------------------------------------------------
// Tag handlers (one per logical UI binding)
// ---------------------------------------------------------------------------

window.tagHandlers = [

  // -------- TempCtrl supervisory --------
  {
    tag: "tic1.sp",
    onUpdate: value => {
      document.getElementById("tc-sp").textContent =
        Number(value).toFixed(1);
    }
  },
  {
    tag: "tic1.tc.mode",
    onUpdate: value => {
      const modes = ["Off", "OperManual", "OperAuto", "PgmAuto"];
      document.getElementById("tc-mode").textContent =
        modes[value] ?? value;
    }
  },
  {
    tag: "tic1.tc.ctrlmode",
    onUpdate: value => {
      const modes = ["Off", "Boost", "FeedFwd", "ClosedLoop"];
      document.getElementById("tc-ctrlmode").textContent =
        modes[value] ?? value;
    }
  },

  // -------- PID internals --------
  {
    tag: "tic1.pid.pv",
    onUpdate: value => {
      document.getElementById("pid-pv").textContent =
        Number(value).toFixed(1);
    }
  },
  {
    tag: "tic1.pid.cv",
    onUpdate: value => {
      document.getElementById("pid-cv").textContent =
        Math.round(value);
    }
  },
  {
  tag: "tic1.tc.mode",
  onUpdate: value => {
    document.querySelectorAll(".mode-btn").forEach(btn => {
      btn.classList.toggle(
        "active",
        parseInt(btn.dataset.mode, 10) === value
      );
      });
    }
  },
  {
  tag: "tic1.sp",
  onUpdate: value => {
    const el = document.getElementById("tc-sp");

    // Avoid cursor jump while user is typing
    if (document.activeElement !== el) {
      el.value = Math.round(value);
      }
    }
  }
];

// ---------------------------------------------------------------------------
// Derive subscriptions automatically
// ---------------------------------------------------------------------------

window.TAG_SUBSCRIPTIONS =
  [...new Set(window.tagHandlers.map(h => h.tag))];

// ---------------------------------------------------------------------------
// Fan-out dispatcher (NEW contract: one argument only)
// ---------------------------------------------------------------------------

window.onTagUpdate = function (tags) {
  //console.log("RUNTIME TAG UPDATE", tags);
  if (!tags || typeof tags !== "object") {
    console.warn("onTagUpdate called with invalid payload:", tags);
    return;
  }

  for (const h of window.tagHandlers) {
    if (h.tag in tags) {
      h.onUpdate(tags[h.tag]);
    }
  }
};

// ---------------------------------------------------------------------------
// Optional: write helpers (future-proofed)
// ---------------------------------------------------------------------------

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

// Example: supervisory setpoint write (when you enable it server-side)
function writeTempSetpoint() {
  const el = document.getElementById("tc-sp");
  const value = parseFloat(el.value);

  if (isNaN(value)) {
    alert("Invalid setpoint");
    return;
  }

  tagWrite("tic1.sp", value);
}




document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const mode = parseInt(btn.dataset.mode, 10);
    tagWrite("tic1.tc.mode", mode);
  });
});

document.getElementById("tc-sp-send").addEventListener("click", () => {
  const el = document.getElementById("tc-sp");
  let value = parseFloat(el.value);

  if (isNaN(value)) return;

  // Clamp defensively (UI + MCU should agree)
  value = Math.max(0, Math.min(500, value));

  tagWrite("tic1.sp", value);
});