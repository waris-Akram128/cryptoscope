
"use strict";

(function () {

    const page = window.location.pathname;

    // ---------------------------------
    // Overview: one-year history chart
    // ---------------------------------

    if (page === "/") {
        createOverviewHistory();
    }

    // ---------------------------------
    // Explorer: one-year option
    // ---------------------------------

    if (page === "/explorer") {
        addYearOption("limit-select", "interval-select");
    }

    // ---------------------------------
    // Compare: one-year option
    // ---------------------------------

    if (page === "/compare") {
        addYearOption("compare-limit", "compare-interval");
    }

    function addYearOption(limitId, intervalId) {
        const limitSelect = document.getElementById(limitId);
        const intervalSelect = document.getElementById(intervalId);

        if (!limitSelect || !intervalSelect) return;

        if (!limitSelect.querySelector('option[value="365"]')) {
            const option = document.createElement("option");

            option.value = "365";
            option.textContent = "1 Year (Daily Candles)";

            limitSelect.appendChild(option);
        }

        // Capture phase: adjust the interval before the
        // existing page's change handler sends its request.
        limitSelect.addEventListener("change", () => {
            if (limitSelect.value === "365") {
                intervalSelect.value = "1d";
            }
        }, true);
    }

    function createOverviewHistory() {
        const watchlist = document.querySelector(".market-card");

        if (!watchlist) return;

        const section = document.createElement("section");
        section.className = "card chart-card";
        section.style.marginBottom = "20px";
        section.style.padding = "20px";

        section.innerHTML = `
            <div class="section-top">
                <div>
                    <h2>Historical Price Performance</h2>
                    <p>
                        Up to one year of completed daily candles
                        from CryptoScope's SQLite database
                    </p>
                </div>
            </div>

            <div style="
                display:flex;
                gap:12px;
                flex-wrap:wrap;
                align-items:center;
                margin:18px 0;
            ">
                <select id="year-coin" style="
                    padding:10px 14px;
                    background:#101b2e;
                    color:#f8fafc;
                    border:1px solid #334155;
                    border-radius:8px;
                ">
                    <option value="BTCUSDT">Bitcoin</option>
                    <option value="ETHUSDT">Ethereum</option>
                    <option value="SOLUSDT">Solana</option>
                    <option value="BNBUSDT">BNB</option>
                    <option value="XRPUSDT">XRP</option>
                </select>

                <select id="year-range" style="
                    padding:10px 14px;
                    background:#101b2e;
                    color:#f8fafc;
                    border:1px solid #334155;
                    border-radius:8px;
                ">
                    <option value="7">7 Days</option>
                    <option value="30">30 Days</option>
                    <option value="90">90 Days</option>
                    <option value="365" selected>1 Year</option>
                </select>

                <span id="year-status"
                      style="font-size:12px;color:#94a3b8;">
                    Loading...
                </span>
            </div>

            <div id="year-chart"
                 style="width:100%;min-height:360px;">
            </div>

            <div id="year-summary"
                 style="font-size:13px;color:#94a3b8;">
            </div>
        `;

        watchlist.parentNode.insertBefore(section, watchlist);

        const coinSelect = document.getElementById("year-coin");
        const rangeSelect = document.getElementById("year-range");

        let history = [];
        let requestId = 0;

        function renderHistory() {
            if (!history.length || !window.Plotly) return;

            const days = Number(rangeSelect.value);
            const candles = history.slice(-days);

            const times = candles.map(c => c.time);
            const prices = candles.map(c => c.close);

            const first = candles[0];
            const last = candles[candles.length - 1];

            const change = (
                (last.close / first.open - 1) * 100
            );

            const color = change >= 0
                ? "#35d1c7"
                : "#fb7185";

            Plotly.react(
                "year-chart",
                [{
                    x: times,
                    y: prices,
                    type: "scatter",
                    mode: "lines",
                    fill: "tozeroy",
                    name: coinSelect.value.replace("USDT", ""),
                    line: {
                        color: color,
                        width: 2.5
                    },
                    fillcolor: change >= 0
                        ? "rgba(53,209,199,0.08)"
                        : "rgba(251,113,133,0.08)"
                }],
                {
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    font: { color: "#94a3b8" },
                    height: 360,
                    autosize: true,
                    margin: {
                        l: 70, r: 20, t: 20, b: 50
                    },
                    xaxis: {
                        type: "date",
                        gridcolor: "#26364e"
                    },
                    yaxis: {
                        title: "Price (USDT)",
                        gridcolor: "#26364e",
                        autorange: true
                    },
                    showlegend: false,
                    hovermode: "x"
                },
                {
                    responsive: true,
                    displayModeBar: false
                }
            );

            document.getElementById("year-summary")
                .textContent =
                `${candles.length} completed daily candles · ` +
                `Period change: ${change >= 0 ? "+" : ""}` +
                `${change.toFixed(2)}% · ` +
                `Last candle: ${last.time.slice(0, 10)} UTC`;
        }

        async function loadHistory() {
            const id = ++requestId;

            document.getElementById("year-status")
                .textContent = "Updating history...";

            try {
                const params = new URLSearchParams({
                    symbol: coinSelect.value,
                    interval: "1d",
                    limit: "365"
                });

                const response = await fetch(
                    `/api/history?${params.toString()}`,
                    { cache: "no-store" }
                );

                const result = await response.json();

                if (id !== requestId) return;

                if (!response.ok) {
                    throw new Error(
                        result.error || "Historical data unavailable"
                    );
                }

                if (!Array.isArray(result.candles) ||
                    !result.candles.length) {
                    throw new Error("No historical candles found");
                }

                history = result.candles;

                renderHistory();

                document.getElementById("year-status")
                    .textContent = result.stale
                    ? "Stored data · Binance update unavailable"
                    : "SQLite history updated";

            } catch (error) {
                if (id !== requestId) return;

                console.error("Year history:", error);

                document.getElementById("year-status")
                    .textContent = error.message;
            }
        }

        coinSelect.addEventListener("change", loadHistory);

        rangeSelect.addEventListener("change", renderHistory);

        loadHistory();

        // Refresh historical data without downloading
        // the complete year again.
        setInterval(loadHistory, 60000);
    }

})();
