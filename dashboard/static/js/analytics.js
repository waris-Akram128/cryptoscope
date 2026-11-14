
"use strict";

const periodSelect = document.getElementById("correlation-days");
const statusEl = document.getElementById("analytics-status");
const timerEl = document.getElementById("analytics-timer");
const errorEl = document.getElementById("analytics-error");

const REFRESH_SECONDS = 60;

let loading = false;
let requestId = 0;
let refreshDeadline = Date.now() + REFRESH_SECONDS * 1000;


function formatCorrelation(value) {
    return value === null ? "N/A" : value.toFixed(3);
}


function updateMetrics(result) {
    const strongest = result.strongest_pair;
    const weakest = result.weakest_pair;

    document.getElementById("strongest-pair").textContent =
        strongest
            ? `${strongest.first} / ${strongest.second}`
            : "N/A";

    document.getElementById("strongest-value").textContent =
        strongest
            ? formatCorrelation(strongest.correlation)
            : "N/A";

    document.getElementById("weakest-pair").textContent =
        weakest
            ? `${weakest.first} / ${weakest.second}`
            : "N/A";

    document.getElementById("weakest-value").textContent =
        weakest
            ? formatCorrelation(weakest.correlation)
            : "N/A";

    document.getElementById("analyzed-days").textContent =
        result.days_analyzed;

    document.getElementById("analytics-period").textContent =
        `${result.period_start.slice(0, 10)} to ` +
        `${result.period_end.slice(0, 10)} UTC`;
}


function drawCorrelation(result) {
    const assets = result.assets;

    const trace = {
        type: "heatmap",
        x: assets,
        y: assets,
        z: result.matrix,

        zmin: -1,
        zmax: 1,
        zmid: 0,

        colorscale: [
            [0, "#ef4444"],
            [0.5, "#172338"],
            [1, "#22c55e"]
        ],

        text: result.matrix.map(row =>
            row.map(value =>
                value === null ? "N/A" : value.toFixed(2)
            )
        ),

        texttemplate: "%{text}",
        textfont: {
            color: "#ffffff",
            size: 13
        },

        hovertemplate:
            "%{y} vs %{x}<br>" +
            "Correlation: %{z:.3f}<extra></extra>",

        colorbar: {
            title: "r",
            tickfont: { color: "#94a3b8" }
        }
    };

    return Plotly.react(
        "correlation-chart",
        [trace],
        {
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#94a3b8" },
            height: 460,
            autosize: true,
            margin: {
                l: 65,
                r: 40,
                t: 30,
                b: 55
            },
            xaxis: { side: "bottom" },
            yaxis: {
                autorange: "reversed"
            }
        },
        {
            responsive: true,
            displaylogo: false
        }
    );
}


function drawVolatility(result) {
    const assets = result.assets;

    const values = assets.map(
        asset => result.volatility[asset]
    );

    return Plotly.react(
        "analytics-volatility",
        [{
            type: "bar",
            x: assets,
            y: values,
            marker: {
                color: "#38bdf8"
            },
            text: values.map(v =>
                v === null ? "N/A" : v.toFixed(3) + "%"
            ),
            textposition: "auto",
            hovertemplate:
                "%{x}<br>Volatility: %{y:.3f}%" +
                "<extra></extra>"
        }],
        {
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#94a3b8" },
            height: 350,
            autosize: true,
            margin: {
                l: 65,
                r: 25,
                t: 25,
                b: 50
            },
            xaxis: {
                showgrid: false
            },
            yaxis: {
                title: "Daily Return Volatility (%)",
                gridcolor: "#26364e"
            }
        },
        {
            responsive: true,
            displaylogo: false
        }
    );
}


async function loadAnalytics() {
    const id = ++requestId;

    loading = true;
    statusEl.textContent = "Analyzing...";
    timerEl.textContent = "Refreshing...";
    errorEl.style.display = "none";

    try {
        const days = periodSelect.value;

        const response = await fetch(
            `/api/analytics/correlation?days=${days}`,
            {
                cache: "no-store",
                signal: AbortSignal.timeout(30000)
            }
        );

        const result = await response.json();

        if (id !== requestId) return;

        if (!response.ok) {
            throw new Error(
                result.error || "Analysis request failed"
            );
        }

        if (!window.Plotly) {
            throw new Error("Plotly library unavailable");
        }

        updateMetrics(result);

        await Promise.all([
            drawCorrelation(result),
            drawVolatility(result)
        ]);

        if (id !== requestId) return;

        statusEl.textContent =
            result.stale
                ? "Stored Data (Update Delayed)"
                : "Analysis Updated";

        document.getElementById("analytics-updated")
            .textContent =
            "Last analyzed: " +
            new Date().toLocaleString();

    } catch (error) {
        if (id !== requestId) return;

        console.error("Analytics error:", error);

        statusEl.textContent = "Analysis Unavailable";

        errorEl.textContent = error.message;
        errorEl.style.display = "block";

    } finally {
        if (id === requestId) {
            loading = false;
            refreshDeadline =
                Date.now() + REFRESH_SECONDS * 1000;
            updateTimer();
        }
    }
}


function updateTimer() {
    if (loading) return;

    const seconds = Math.max(
        0,
        Math.ceil((refreshDeadline - Date.now()) / 1000)
    );

    timerEl.textContent = `Refresh in ${seconds}s`;

    if (seconds === 0) {
        loadAnalytics();
    }
}


periodSelect.addEventListener("change", loadAnalytics);

loadAnalytics();

setInterval(updateTimer, 1000);
