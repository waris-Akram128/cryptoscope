
"use strict";

const firstSelect = document.getElementById("asset-one");
const secondSelect = document.getElementById("asset-two");
const intervalSelect = document.getElementById("compare-interval");
const limitSelect = document.getElementById("compare-limit");

const statusEl = document.getElementById("compare-status");
const timerEl = document.getElementById("compare-timer");
const errorEl = document.getElementById("compare-error");

const REFRESH_SECONDS = 60;
const COLORS = ["#38bdf8", "#a78bfa"];

let requestId = 0;
let loading = false;
let nextRefresh = Date.now() + 60000;


// ----------------------------------
// Formatting
// ----------------------------------

function shortName(symbol) {
    return symbol.replace("USDT", "");
}

function formatPrice(value) {
    return "$" + Number(value).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: value < 1 ? 6 : 2
    });
}

function formatPercent(value) {
    return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}


// ----------------------------------
// Statistics
// ----------------------------------

function mean(values) {
    return values.reduce((a, b) => a + b, 0) / values.length;
}

function getReturns(prices) {
    const result = [];

    for (let i = 1; i < prices.length; i++) {
        result.push(
            ((prices[i] / prices[i - 1]) - 1) * 100
        );
    }

    return result;
}

function volatility(values) {
    if (values.length < 2) return null;

    const avg = mean(values);

    const variance = values.reduce(
        (sum, value) => sum + (value - avg) ** 2,
        0
    ) / (values.length - 1);

    return Math.sqrt(variance);
}

function correlation(a, b) {
    if (a.length !== b.length || a.length < 2) {
        return null;
    }

    const avgA = mean(a);
    const avgB = mean(b);

    let numerator = 0;
    let sumA = 0;
    let sumB = 0;

    for (let i = 0; i < a.length; i++) {
        const x = a[i] - avgA;
        const y = b[i] - avgB;

        numerator += x * y;
        sumA += x * x;
        sumB += y * y;
    }

    const denominator = Math.sqrt(sumA * sumB);

    return denominator === 0
        ? null
        : numerator / denominator;
}


// ----------------------------------
// API
// ----------------------------------

async function fetchHistory(symbol, interval, limit) {
    const params = new URLSearchParams({
        symbol,
        interval,
        limit
    });

    const response = await fetch(
        `/api/history?${params}`,
        {
            cache: "no-store",
            signal: AbortSignal.timeout(20000)
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || `Failed to load ${symbol}`
        );
    }

    if (!Array.isArray(data.candles)) {
        throw new Error(`Invalid data for ${symbol}`);
    }

    return data.candles;
}


// ----------------------------------
// Align both cryptocurrencies
// ----------------------------------

function alignData(candlesA, candlesB) {
    const mapB = new Map(
        candlesB.map(c => [c.time, c])
    );

    const a = [];
    const b = [];

    for (const candle of candlesA) {
        const match = mapB.get(candle.time);

        if (match) {
            a.push(candle);
            b.push(match);
        }
    }

    if (a.length < 3) {
        throw new Error("Not enough matching candles");
    }

    return { a, b };
}


// ----------------------------------
// Charts
// ----------------------------------

function baseLayout(title, height = 380) {
    return {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#94a3b8" },
        height,
        margin: { l: 65, r: 25, t: 35, b: 50 },
        autosize: true,
        hovermode: "x unified",
        xaxis: {
            gridcolor: "#26364e"
        },
        yaxis: {
            title,
            gridcolor: "#26364e"
        },
        legend: {
            orientation: "h",
            y: 1.15
        }
    };
}

function drawCharts(a, b, nameA, nameB, volA, volB) {
    const times = a.map(c => c.time);

    const pricesA = a.map(c => c.close);
    const pricesB = b.map(c => c.close);

    const normalizedA = pricesA.map(
        p => (p / pricesA[0]) * 100
    );

    const normalizedB = pricesB.map(
        p => (p / pricesB[0]) * 100
    );

    Plotly.react(
        "performance-chart",
        [
            {
                x: times,
                y: normalizedA,
                type: "scatter",
                mode: "lines",
                name: nameA,
                line: {
                    color: COLORS[0],
                    width: 2.5
                }
            },
            {
                x: times,
                y: normalizedB,
                type: "scatter",
                mode: "lines",
                name: nameB,
                line: {
                    color: COLORS[1],
                    width: 2.5
                }
            }
        ],
        baseLayout("Normalized Price"),
        { responsive: true, displaylogo: false }
    );

    Plotly.react(
        "volatility-chart",
        [{
            x: [nameA, nameB],
            y: [volA, volB],
            type: "bar",
            marker: { color: COLORS },
            text: [volA, volB].map(
                v => v === null ? "N/A" : v.toFixed(3) + "%"
            ),
            textposition: "auto"
        }],
        {
            ...baseLayout("Return Volatility (%)", 320),
            showlegend: false
        },
        { responsive: true, displaylogo: false }
    );
}


// ----------------------------------
// Table
// ----------------------------------

function updateTable(a, b, nameA, nameB, retA, retB, volA, volB) {
    document.getElementById("asset-one-heading").textContent = nameA;
    document.getElementById("asset-two-heading").textContent = nameB;

    const rows = [
        ["First Close", formatPrice(a[0].close), formatPrice(b[0].close)],
        ["Latest Close", formatPrice(a.at(-1).close), formatPrice(b.at(-1).close)],
        ["Period Return", formatPercent(retA), formatPercent(retB)],
        [
            "Return Volatility",
            volA === null ? "N/A" : volA.toFixed(3) + "%",
            volB === null ? "N/A" : volB.toFixed(3) + "%"
        ],
        [
            "Highest Price",
            formatPrice(Math.max(...a.map(c => c.high))),
            formatPrice(Math.max(...b.map(c => c.high)))
        ],
        [
            "Lowest Price",
            formatPrice(Math.min(...a.map(c => c.low))),
            formatPrice(Math.min(...b.map(c => c.low)))
        ],
        ["Matched Candles", String(a.length), String(b.length)]
    ];

    const tbody = document.getElementById("comparison-table");
    tbody.replaceChildren();

    rows.forEach(values => {
        const tr = document.createElement("tr");

        values.forEach(value => {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}


// ----------------------------------
// Main Comparison
// ----------------------------------

async function loadComparison() {
    const id = ++requestId;

    const symbolA = firstSelect.value;
    const symbolB = secondSelect.value;
    const interval = intervalSelect.value;
    const limit = limitSelect.value;

    loading = true;
    statusEl.textContent = "Loading...";
    timerEl.textContent = "Refreshing...";
    errorEl.style.display = "none";

    try {
        if (symbolA === symbolB) {
            throw new Error("Select two different cryptocurrencies");
        }

        if (!window.Plotly) {
            throw new Error("Plotly is not loaded");
        }

        console.log("Fetching:", symbolA, symbolB);

        const [candlesA, candlesB] = await Promise.all([
            fetchHistory(symbolA, interval, limit),
            fetchHistory(symbolB, interval, limit)
        ]);

        if (id !== requestId) return;

        const { a, b } = alignData(candlesA, candlesB);

        const pricesA = a.map(c => c.close);
        const pricesB = b.map(c => c.close);

        const returnsA = getReturns(pricesA);
        const returnsB = getReturns(pricesB);

        const returnA =
            (pricesA.at(-1) / pricesA[0] - 1) * 100;

        const returnB =
            (pricesB.at(-1) / pricesB[0] - 1) * 100;

        const volA = volatility(returnsA);
        const volB = volatility(returnsB);
        const corr = correlation(returnsA, returnsB);

        const nameA = shortName(symbolA);
        const nameB = shortName(symbolB);

        document.getElementById("best-performer").textContent =
            returnA >= returnB ? nameA : nameB;

        document.getElementById("return-difference").textContent =
            Math.abs(returnA - returnB).toFixed(2) + " pp";

        document.getElementById("return-correlation").textContent =
            corr === null ? "N/A" : corr.toFixed(3);

        document.getElementById("higher-volatility").textContent =
            volA === null || volB === null
                ? "N/A"
                : volA >= volB ? nameA : nameB;

        updateTable(
            a, b, nameA, nameB,
            returnA, returnB, volA, volB
        );

        await drawCharts(a, b, nameA, nameB, volA, volB);

        statusEl.textContent = "Market Data Connected";

        document.getElementById("compare-updated").textContent =
            "Updated: " + new Date().toLocaleString();

        console.log("Comparison loaded successfully");

    } catch (error) {
        if (id !== requestId) return;

        console.error("Compare Assets error:", error);

        statusEl.textContent = "Data Unavailable";
        errorEl.textContent = error.message;
        errorEl.style.display = "block";

    } finally {
        if (id === requestId) {
            loading = false;
            nextRefresh = Date.now() + REFRESH_SECONDS * 1000;
            updateTimer();
        }
    }
}


// ----------------------------------
// Countdown
// ----------------------------------

function updateTimer() {
    if (loading) return;

    const seconds = Math.max(
        0,
        Math.ceil((nextRefresh - Date.now()) / 1000)
    );

    timerEl.textContent = `Refresh in ${seconds}s`;

    if (seconds === 0) {
        loadComparison();
    }
}


// ----------------------------------
// Events
// ----------------------------------

firstSelect.addEventListener("change", loadComparison);
secondSelect.addEventListener("change", loadComparison);
intervalSelect.addEventListener("change", loadComparison);
limitSelect.addEventListener("change", loadComparison);

loadComparison();

setInterval(updateTimer, 1000);
