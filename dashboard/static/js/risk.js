
"use strict";

const riskCoin = document.getElementById("risk-coin");
const riskDays = document.getElementById("risk-days");
const riskStatus = document.getElementById("risk-status");
const riskError = document.getElementById("risk-error");

let riskRequestId = 0;

function riskLayout(title, height = 360) {
    return {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#94a3b8" },
        height,
        autosize: true,
        margin: { l: 70, r: 25, t: 25, b: 50 },
        xaxis: {
            gridcolor: "#26364e"
        },
        yaxis: {
            title,
            gridcolor: "#26364e",
            zerolinecolor: "#64748b"
        },
        showlegend: false
    };
}

function riskPercent(value) {
    return (value >= 0 ? "+" : "") + value.toFixed(3) + "%";
}

function displayRiskMetrics(data) {
    const summary = data.summary;

    document.getElementById("risk-average").textContent =
        riskPercent(summary.mean_daily_return);

    document.getElementById("risk-volatility").textContent =
        summary.daily_volatility.toFixed(3) + "%";

    document.getElementById("risk-anomalies").textContent =
        summary.anomaly_count;
}

function drawReturnDistribution(records) {
    const values = records.map(r => r.return);

    return Plotly.react(
        "return-distribution",
        [{
            x: values,
            type: "histogram",
            nbinsx: 35,
            marker: { color: "#38bdf8" },
            hovertemplate:
                "Daily Return: %{x:.2f}%<br>" +
                "Frequency: %{y}<extra></extra>"
        }],
        {
            ...riskLayout("Number of Days"),
            xaxis: {
                title: "Daily Return (%)",
                gridcolor: "#26364e"
            }
        },
        { responsive: true, displaylogo: false }
    );
}

function drawRollingVolatility(records) {
    return Plotly.react(
        "rolling-volatility",
        [{
            x: records.map(r => r.time),
            y: records.map(r => r.rolling_volatility),
            type: "scatter",
            mode: "lines",
            line: {
                color: "#a78bfa",
                width: 2.5
            },
            hovertemplate:
                "%{x}<br>Volatility: %{y:.3f}%" +
                "<extra></extra>"
        }],
        riskLayout("30-Day Volatility (%)"),
        { responsive: true, displaylogo: false }
    );
}

function drawAnomalies(records) {
    const unusual = records.filter(r => r.anomaly);

    return Plotly.react(
        "anomaly-chart",
        [
            {
                x: records.map(r => r.time),
                y: records.map(r => r.return),
                type: "scatter",
                mode: "lines",
                name: "Daily Return",
                line: {
                    color: "#38bdf8",
                    width: 1.8
                }
            },
            {
                x: unusual.map(r => r.time),
                y: unusual.map(r => r.return),
                type: "scatter",
                mode: "markers",
                name: "Unusual Movement",
                marker: {
                    color: "#fb7185",
                    size: 10,
                    symbol: "circle",
                    line: {
                        color: "#ffffff",
                        width: 1
                    }
                }
            }
        ],
        {
            ...riskLayout("Daily Return (%)"),
            showlegend: true,
            legend: {
                orientation: "h",
                y: 1.15
            }
        },
        { responsive: true, displaylogo: false }
    );
}

async function loadRiskAnalysis() {
    const id = ++riskRequestId;

    riskStatus.textContent = "Analyzing...";
    riskError.style.display = "none";

    const params = new URLSearchParams({
        symbol: riskCoin.value,
        days: riskDays.value
    });

    try {
        const response = await fetch(
            `/api/analytics/risk?${params}`,
            { cache: "no-store" }
        );

        const data = await response.json();

        if (id !== riskRequestId) return;

        if (!response.ok) {
            throw new Error(
                data.error || "Risk analysis unavailable"
            );
        }

        if (!window.Plotly) {
            throw new Error("Plotly library unavailable");
        }

        displayRiskMetrics(data);

        await Promise.all([
            drawReturnDistribution(data.records),
            drawRollingVolatility(data.records),
            drawAnomalies(data.records)
        ]);

        if (id !== riskRequestId) return;

        riskStatus.textContent = data.stale
            ? "Stored Data (Update Delayed)"
            : `${data.days_analyzed} Daily Returns Analyzed`;

    } catch (error) {
        if (id !== riskRequestId) return;

        console.error("Risk analysis:", error);

        riskStatus.textContent = "Analysis Unavailable";
        riskError.textContent = error.message;
        riskError.style.display = "block";
    }
}

riskCoin.addEventListener("change", loadRiskAnalysis);
riskDays.addEventListener("change", loadRiskAnalysis);

loadRiskAnalysis();

// Refresh the analytics every 60 seconds.
setInterval(loadRiskAnalysis, 60000);
