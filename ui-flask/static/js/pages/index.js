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

// Derive subscriptions automatically
window.TAG_SUBSCRIPTIONS =
  [...new Set(window.tagHandlers.map(h => h.tag))];

// Fan-out dispatcher
window.onTagUpdate = function (tags) {
  for (const h of window.tagHandlers) {
    if (h.tag in tags) {
      h.onUpdate(tags[h.tag]);
    }
  }
};
