
const API_URL = "/api/markets";
const REFRESH_INTERVAL = 60;
let countdown = REFRESH_INTERVAL;
let isRefreshing = false;

function formatPrice(value) {
    const digits = value < 1 ? 6 : value < 100 ? 4 : 2;

    return "$" + value.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: digits
    });
}

function formatVolume(value) {
    if (value >= 1e9) {
        return "$" + (value / 1e9).toFixed(2) + "B";
    }

    if (value >= 1e6) {
        return "$" + (value / 1e6).toFixed(2) + "M";
    }

    return "$" + value.toLocaleString("en-US", {
        maximumFractionDigits: 0
    });
}

function formatChange(value) {
    return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}

function updateTimer() {
    const timer = document.getElementById("refresh-timer");

    if (!timer) return;

    if (isRefreshing) {
        timer.textContent = "Refreshing...";
    } else {
        timer.textContent = `Next refresh in ${countdown}s`;
    }
}

function updateSummary(markets, stale) {
    document.getElementById("tracked-assets").textContent =
        markets.length;

    const sorted = [...markets].sort(
        (a, b) => b.change - a.change
    );

    const gainer = sorted[0];
    const loser = sorted[sorted.length - 1];

    const volumeLeader = [...markets].sort(
        (a, b) => b.volume - a.volume
    )[0];

    const totalVolume = markets.reduce(
        (total, coin) => total + coin.volume, 0
    );

    document.getElementById("top-gainer").textContent =
        gainer.symbol + " " + formatChange(gainer.change);

    document.getElementById("total-volume").textContent =
        formatVolume(totalVolume);

    document.getElementById("feed-status").textContent =
        stale ? "Cached Data" : "Connected";

    document.getElementById("market-status").textContent =
        stale ? "Data may be outdated" : "Market Data Connected";

    document.getElementById("insight-gainer").textContent =
        gainer.symbol + ": " + formatChange(gainer.change);

    document.getElementById("insight-loser").textContent =
        loser.symbol + ": " + formatChange(loser.change);

    document.getElementById("insight-volume").textContent =
        volumeLeader.symbol + ": " +
        formatVolume(volumeLeader.volume);
}

function updateTable(markets) {
    const tbody = document.getElementById("market-table");

    tbody.replaceChildren();

    markets.forEach(coin => {
        const row = document.createElement("tr");

        const cells = [
            coin.name + " (" + coin.symbol + ")",
            formatPrice(coin.price),
            formatChange(coin.change),
            formatPrice(coin.high),
            formatPrice(coin.low),
            formatVolume(coin.volume)
        ];

        cells.forEach((value, index) => {
            const td = document.createElement("td");

            td.textContent = value;

            if (index === 2) {
                td.className = coin.change >= 0
                    ? "positive"
                    : "negative";
            }

            row.appendChild(td);
        });

        tbody.appendChild(row);
    });
}

function updateChart(markets) {
    const element = document.getElementById("change-chart");

    if (!window.Plotly) {
        element.textContent = "Chart library unavailable.";
        return;
    }

    const colors = markets.map(
        coin => coin.change >= 0 ? "#35d1c7" : "#fb7185"
    );

    const data = [{
        x: markets.map(coin => coin.symbol),
        y: markets.map(coin => coin.change),
        type: "bar",
        marker: { color: colors },
        hovertemplate: "%{x}: %{y:.2f}%<extra></extra>"
    }];

    const layout = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#94a3b8" },
        margin: { t: 15, r: 15, b: 40, l: 50 },
        height: 300,
        autosize: true,
        xaxis: {
            showgrid: false
        },
        yaxis: {
            title: "Change (%)",
            gridcolor: "#26364e",
            zerolinecolor: "#64748b"
        }
    };

    Plotly.react(element, data, layout, {
        responsive: true,
        displayModeBar: false
    });
}

async function loadMarkets() {
    if (isRefreshing) return;

    isRefreshing = true;
    updateTimer();

    try {
        const response = await fetch(API_URL, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Market API request failed");
        }

        const result = await response.json();
        const markets = result.markets;

        if (!Array.isArray(markets) || markets.length === 0) {
            throw new Error("No market data available");
        }

        updateSummary(markets, result.stale);
        updateTable(markets);
        updateChart(markets);

        const updatedTime = new Date(result.updated_at);

        document.getElementById("last-update").textContent =
            "Last updated: " + updatedTime.toLocaleString();

    } catch (error) {
        console.error("CryptoScope:", error);

        document.getElementById("market-status").textContent =
            "Connection Error";

        document.getElementById("feed-status").textContent =
            "Unavailable";

    } finally {
        isRefreshing = false;
        countdown = REFRESH_INTERVAL;
        updateTimer();
    }
}

// Refresh every second and decrease countdown.
setInterval(() => {
    if (isRefreshing) return;

    countdown--;

    if (countdown <= 0) {
        loadMarkets();
    } else {
        updateTimer();
    }
}, 1000);

// Initial request
loadMarkets();
