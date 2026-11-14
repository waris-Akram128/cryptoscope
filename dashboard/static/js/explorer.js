
const coinSelect = document.getElementById("coin-select");
const intervalSelect = document.getElementById("interval-select");
const limitSelect = document.getElementById("limit-select");
const chartTypeSelect = document.getElementById("chart-type");

const sma20Checkbox = document.getElementById("show-sma20");
const sma50Checkbox = document.getElementById("show-sma50");

const explorerStatus = document.getElementById("explorer-status");
const explorerError = document.getElementById("explorer-error");
const refreshCountdown = document.getElementById("refresh-countdown");

const REFRESH_SECONDS = 60;

let remainingSeconds = REFRESH_SECONDS;
let isLoading = false;
let requestId = 0;
let currentData = null;
let refreshDeadline = Date.now() + REFRESH_SECONDS * 1000;


// -------------------------------
// Formatting
// -------------------------------

function formatPrice(value) {
    const digits = value < 1 ? 6 : value < 100 ? 4 : 2;

    return "$" + Number(value).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: digits
    });
}

function formatNumber(value) {
    return Number(value).toLocaleString("en-US", {
        maximumFractionDigits: 0
    });
}

function formatVolume(value) {
    if (value >= 1e9) {
        return "$" + (value / 1e9).toFixed(2) + "B";
    }

    if (value >= 1e6) {
        return "$" + (value / 1e6).toFixed(2) + "M";
    }

    if (value >= 1e3) {
        return "$" + (value / 1e3).toFixed(2) + "K";
    }

    return formatPrice(value);
}


// -------------------------------
// Moving Average Calculation
// -------------------------------

function calculateSMA(candles, period) {
    const result = [];
    let sum = 0;

    for (let i = 0; i < candles.length; i++) {
        sum += candles[i].close;

        if (i >= period) {
            sum -= candles[i - period].close;
        }

        if (i >= period - 1) {
            result.push(sum / period);
        } else {
            result.push(null);
        }
    }

    return result;
}


// -------------------------------
// Metrics
// -------------------------------

function updateMetrics(summary) {
    document.getElementById("metric-price").textContent =
        formatPrice(summary.latest_price);

    const changeElement = document.getElementById("metric-change");

    changeElement.textContent =
        (summary.change >= 0 ? "+" : "") +
        summary.change.toFixed(2) + "%";

    changeElement.style.color =
        summary.change >= 0 ? "#35d1c7" : "#fb7185";

    document.getElementById("metric-high").textContent =
        formatPrice(summary.highest);

    document.getElementById("metric-low").textContent =
        formatPrice(summary.lowest);

    document.getElementById("metric-volume").textContent =
        formatVolume(summary.quote_volume);

    document.getElementById("metric-trades").textContent =
        formatNumber(summary.total_trades);
}


// -------------------------------
// Plotly Chart Layout
// -------------------------------

function chartLayout(yTitle, height = 440) {
    return {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",

        font: {
            color: "#94a3b8",
            size: 12
        },

        margin: {
            l: 70,
            r: 25,
            t: 30,
            b: 50
        },

        height: height,
        autosize: true,

        xaxis: {
            type: "date",
            gridcolor: "#26364e",
            rangeslider: {
                visible: false
            }
        },

        yaxis: {
            title: yTitle,
            gridcolor: "#26364e",
            autorange: true
        },

        hovermode: "x unified",

        legend: {
            orientation: "h",
            x: 0,
            y: 1.12,
            font: {
                color: "#cbd5e1"
            }
        }
    };
}


// -------------------------------
// Price Chart
// -------------------------------

function drawPriceChart(candles, symbol) {
    const times = candles.map(c => c.time);
    const traces = [];

    const chartType = chartTypeSelect.value;

    if (chartType === "candlestick") {
        traces.push({
            x: times,
            open: candles.map(c => c.open),
            high: candles.map(c => c.high),
            low: candles.map(c => c.low),
            close: candles.map(c => c.close),

            type: "candlestick",
            name: symbol,

            increasing: {
                line: {
                    color: "#35d1c7"
                }
            },

            decreasing: {
                line: {
                    color: "#fb7185"
                }
            }
        });
    } else {
        traces.push({
            x: times,
            y: candles.map(c => c.close),

            type: "scatter",
            mode: "lines",
            name: "Closing Price",

            line: {
                color: "#38bdf8",
                width: 2.5
            }
        });
    }

    // SMA 20
    if (sma20Checkbox.checked) {
        traces.push({
            x: times,
            y: calculateSMA(candles, 20),

            type: "scatter",
            mode: "lines",
            name: "SMA 20",

            line: {
                color: "#fbbf24",
                width: 2
            },

            hovertemplate:
                "SMA 20: %{y:,.4f}<extra></extra>"
        });
    }

    // SMA 50
    if (sma50Checkbox.checked) {
        traces.push({
            x: times,
            y: calculateSMA(candles, 50),

            type: "scatter",
            mode: "lines",
            name: "SMA 50",

            line: {
                color: "#a78bfa",
                width: 2
            },

            hovertemplate:
                "SMA 50: %{y:,.4f}<extra></extra>"
        });
    }

    Plotly.react(
        "candlestick-chart",
        traces,
        chartLayout("Price (USDT)"),
        {
            responsive: true,
            displaylogo: false,
            scrollZoom: true
        }
    );
}


// -------------------------------
// Volume Chart
// -------------------------------

function drawVolumeChart(candles) {
    const colors = candles.map(c =>
        c.close >= c.open ? "#35d1c7" : "#fb7185"
    );

    const trace = {
        x: candles.map(c => c.time),
        y: candles.map(c => c.volume),

        type: "bar",

        marker: {
            color: colors
        },

        name: "Trading Volume",

        hovertemplate:
            "%{x}<br>Volume: %{y:,.2f}<extra></extra>"
    };

    Plotly.react(
        "volume-chart",
        [trace],
        {
            ...chartLayout("Base Asset Volume", 300),
            showlegend: false
        },
        {
            responsive: true,
            displaylogo: false
        }
    );
}


// -------------------------------
// Render Charts
// -------------------------------

function renderCharts() {
    if (!currentData || !window.Plotly) {
        return;
    }

    drawPriceChart(
        currentData.candles,
        currentData.symbol
    );

    drawVolumeChart(currentData.candles);
}


// -------------------------------
// API Request
// -------------------------------

async function loadExplorer() {
    const id = ++requestId;

    const symbol = coinSelect.value;
    const interval = intervalSelect.value;
    const limit = limitSelect.value;

    isLoading = true;
    explorerStatus.textContent = "Refreshing...";
    explorerError.style.display = "none";
    refreshCountdown.textContent = "Refreshing...";

    const params = new URLSearchParams({
        symbol,
        interval,
        limit
    });

    try {
        const response = await fetch(
            `/api/history?${params.toString()}`,
            {
                cache: "no-store"
            }
        );

        const result = await response.json();

        if (id !== requestId) return;

        if (!response.ok) {
            throw new Error(
                result.error || "Failed to fetch market data"
            );
        }

        if (!result.candles || !result.candles.length) {
            throw new Error("No candle data available");
        }

        if (!window.Plotly) {
            throw new Error("Plotly library unavailable");
        }

        currentData = result;

        updateMetrics(result.summary);
        renderCharts();

        explorerStatus.textContent = "Market Data Connected";

        document.getElementById("explorer-updated").textContent =
            "Updated: " +
            new Date(result.updated_at).toLocaleString();

    } catch (error) {
        if (id !== requestId) return;

        explorerStatus.textContent = "Data Unavailable";

        explorerError.textContent = error.message;
        explorerError.style.display = "block";

        console.error("CryptoScope Explorer:", error);

    } finally {
        if (id === requestId) {
            isLoading = false;

            remainingSeconds = REFRESH_SECONDS;
            refreshDeadline =
                Date.now() + REFRESH_SECONDS * 1000;

            updateCountdown();
        }
    }
}


// -------------------------------
// Countdown Timer
// -------------------------------

function updateCountdown() {
    if (isLoading) {
        refreshCountdown.textContent = "Refreshing...";
        return;
    }

    remainingSeconds = Math.max(
        0,
        Math.ceil((refreshDeadline - Date.now()) / 1000)
    );

    refreshCountdown.textContent =
        `Refresh in ${remainingSeconds}s`;

    if (remainingSeconds === 0) {
        loadExplorer();
    }
}


// -------------------------------
// Event Listeners
// -------------------------------

coinSelect.addEventListener("change", loadExplorer);
intervalSelect.addEventListener("change", loadExplorer);
limitSelect.addEventListener("change", loadExplorer);

chartTypeSelect.addEventListener("change", renderCharts);
sma20Checkbox.addEventListener("change", renderCharts);
sma50Checkbox.addEventListener("change", renderCharts);


// Initial data load
loadExplorer();

// Live countdown
setInterval(updateCountdown, 1000);
