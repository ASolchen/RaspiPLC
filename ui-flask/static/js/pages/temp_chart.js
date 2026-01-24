console.log("Temp chart JS loaded (historian-backed)");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const TAGS = [
  "tic1.pid.pv",
  "tic1.sp",
  "tic1.pid.cv"
];

let lastPV = null;
let lastSP = null;
let lastCV = null;

const WINDOW_MS = 60 * 60 * 1000; // 1 hour
const POLL_INTERVAL_MS = 2000;   // tail poll every 2 seconds

// ---------------------------------------------------------------------------
// Chart setup
// ---------------------------------------------------------------------------

const ctx = document.getElementById("tempChart").getContext("2d");

const chart = new Chart(ctx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "Process Temp (°F)",
        data: [],
        borderWidth: 2,
        stepped: true,
        pointRadius: 0,
      },
      {
        label: "Setpoint (°F)",
        data: [],
        borderDash: [6, 4],
        borderWidth: 2,
        stepped: true,
        pointRadius: 0,
      },
      {
        label: "Control Output (%)",
        data: [],
        borderWidth: 1,
        stepped: true,
        pointRadius: 0,
        yAxisID: "y2",
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: {
      intersect: false,
      mode: "nearest"
    },
    scales: {
      x: {
        type: "time",
        time: {
          unit: "minute",
          tooltipFormat: "HH:mm:ss"
        }
      },
      y: {
        min: 0,
        max: 500,
        title: {
          display: true,
          text: "Temperature (°F)"
        }
      },
      y2: {
        type: "linear", 
        position: "right",
        min: 0,
        max: 100,
        grid: {
          drawOnChartArea: false
        },
        title: {
          display: true,
          text: "CV (%)"
        }
      }
    },
    plugins: {
      legend: {
        position: "top"
      }
    }
  }
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let lastEndTs = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function nowMs() {
  return Date.now();
}

function apiHistory(start, end) {
  const params = new URLSearchParams({
    tags: TAGS.join(","),
    start: start.toString(),
    end: end.toString()
  });

  return fetch(`/api/history?${params}`)
    .then(res => {
      if (!res.ok) {
        throw new Error(`History API error: ${res.status}`);
      }
      return res.json();
    });
}

function appendRows(rows) {
  for (const row of rows) {
    const ts = row.ts;
    const tag = row.tag;
    const value = row.value;

    if (tag === "tic1.pid.pv") lastPV = value;
    if (tag === "tic1.sp")     lastSP = value;
    if (tag === "tic1.pid.cv") lastCV = value;

    chart.data.labels.push(new Date(ts));
    chart.data.datasets[0].data.push(lastPV);
    chart.data.datasets[1].data.push(lastSP);
    chart.data.datasets[2].data.push(lastCV);
  }
}

function trimWindow(endTs) {
  const minTs = endTs - WINDOW_MS;

  while (chart.data.labels.length > 0 &&
         chart.data.labels[0].getTime() < minTs) {

    chart.data.labels.shift();
    chart.data.datasets.forEach(ds => ds.data.shift());
  }

  chart.options.scales.x.min = minTs;
  chart.options.scales.x.max = endTs;
}

// ---------------------------------------------------------------------------
// Initial backfill
// ---------------------------------------------------------------------------

(function initialLoad() {
  const end = nowMs();
  const start = end - WINDOW_MS;

  console.log("Initial history load");

  apiHistory(start, end)
    .then(payload => {
      appendRows(payload.rows);

      lastEndTs = payload.end;

      trimWindow(lastEndTs);
      chart.update("none");

      startTailPolling();
    })
    .catch(err => {
      console.error("Initial history load failed:", err);
    });
})();

// ---------------------------------------------------------------------------
// Tail polling
// ---------------------------------------------------------------------------

function startTailPolling() {
  console.log("Starting tail polling");

  setInterval(() => {
    if (lastEndTs === null) return;

    const end = nowMs();

    apiHistory(lastEndTs, end)
      .then(payload => {
        if (payload.rows.length > 0) {
          appendRows(payload.rows);
        }

        lastEndTs = payload.end;

        trimWindow(lastEndTs);
        chart.update("none");
      })
      .catch(err => {
        console.warn("Tail poll failed:", err);
      });

  }, POLL_INTERVAL_MS);
}
