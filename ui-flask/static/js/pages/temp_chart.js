
console.log("Temp chart JS loaded (record-based historian)");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const TAGS = [
  "tic1.pid.pv",
  "tic1.sp",
  "tic1.pid.cv"
];

const WINDOW_MS = 60 * 60 * 1000;   // visible window (1 hour)
const FETCH_LIMIT = 300;            // records per request
const POLL_IDLE_MS = 2000;          // delay when caught up

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
        stepped: true,
        pointRadius: 0,
        borderWidth: 2,
        yAxisID: "y"
      },
      {
        label: "Setpoint (°F)",
        data: [],
        stepped: true,
        pointRadius: 0,
        borderDash: [6, 4],
        borderWidth: 2,
        yAxisID: "y"
      },
      {
        label: "Control Output (%)",
        data: [],
        stepped: true,
        pointRadius: 0,
        borderWidth: 1,
        yAxisID: "y2"
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: "time",
        ticks: {
          color: "#fff"
        },
        grid: {
          display: true,
          color: "rgba(255,255,255,0.15)"   // ← vertical grid lines
        }
      },
      y: {
        type: "linear",
        min: 0,
        max: 500,
        ticks: {
          color: "#fff"
        },
        grid: {
          display: true,
          color: "rgba(255,255,255,0.15)"   // ← horizontal grid lines
        },
        title: { display: true, text: "Temperature (°F)" }
      },
      y2: {
        type: "linear",
        position: "right",
        min: 0,
        max: 100,
        grid: { drawOnChartArea: false },
        title: { display: true, text: "CV (%)" }
      }
    }
  }
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let cursorTs = null;
let loading = false;

let lastPV = null;
let lastSP = null;
let lastCV = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function trimWindow() {
  const minTs = Date.now() - WINDOW_MS;

  while (
    chart.data.labels.length > 0 &&
    chart.data.labels[0].getTime() < minTs
  ) {
    chart.data.labels.shift();
    chart.data.datasets.forEach(ds => ds.data.shift());
  }

  chart.options.scales.x.max = Date.now();
  chart.options.scales.x.min = minTs;
}

function appendRows(rows) {
  let ts = 0 
  for (const row of rows) {
    if (true){ //only push new values every second
      ts = row.timestamp
      //console.log(row)
      if (row.tag === "tic1.pid.pv") lastPV = row.value;
      if (row.tag === "tic1.sp")     lastSP = row.value;
      if (row.tag === "tic1.pid.cv") lastCV = row.value;

      chart.data.labels.push(new Date(ts));
      chart.data.datasets[0].data.push(lastPV);
      chart.data.datasets[1].data.push(lastSP);
      chart.data.datasets[2].data.push(lastCV);
    }
  }
}

// ---------------------------------------------------------------------------
// Unified fetch loop (record-based)
// ---------------------------------------------------------------------------

function fetchHistoryStep() {
  if (loading) return;
  loading = true;

  const params = new URLSearchParams({
    tags: TAGS.join(","),
    limit: FETCH_LIMIT
  });

  if (cursorTs !== null) {
    params.set("after", cursorTs.toString());
  }

  fetch(`/api/history?${params}`)
    .then(res => {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    })
    .then(payload => {
      if (payload.rows.length > 0) {
        appendRows(payload.rows);
        chart.update("none");

        cursorTs = payload.rows[payload.rows.length - 1].ts;
        trimWindow();

        loading = false;
        //console.log("Recieved "+ payload.rows.length + " samples")
        // If we got a full chunk, more data likely exists
        if (payload.rows.length === FETCH_LIMIT) {
          setTimeout(fetchHistoryStep, 0);
        } else {
          setTimeout(fetchHistoryStep, POLL_IDLE_MS);
        }
      } else {
        loading = false;
        setTimeout(fetchHistoryStep, POLL_IDLE_MS);
      }
    })
    .catch(err => {
      console.warn("History fetch failed:", err);
      loading = false;
      setTimeout(fetchHistoryStep, POLL_IDLE_MS);
    });
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

fetchHistoryStep();
