
"use strict";

const symbolInput = document.getElementById("data-symbol");
const startInput = document.getElementById("data-start");
const endInput = document.getElementById("data-end");
const pageSizeInput = document.getElementById("data-page-size");

const tableBody = document.getElementById("data-table-body");
const statusEl = document.getElementById("data-status");
const errorEl = document.getElementById("data-error");

const previousButton = document.getElementById("previous-page");
const nextButton = document.getElementById("next-page");
const exportButton = document.getElementById("export-csv");

let currentPage = 1;
let totalPages = 1;
let requestId = 0;
let activeFilters = null;


function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) {
        return "--";
    }

    return Number(value).toLocaleString("en-US", {
        maximumFractionDigits: decimals
    });
}

function formatDate(value) {
    return value ? value + " UTC" : "--";
}

function getFilters() {
    return {
        symbol: symbolInput.value,
        start: startInput.value,
        end: endInput.value,
        page_size: pageSizeInput.value
    };
}

function createParams(filters, page) {
    const params = new URLSearchParams();

    if (filters.symbol) {
        params.set("symbol", filters.symbol);
    }

    if (filters.start) {
        params.set("start", filters.start);
    }

    if (filters.end) {
        params.set("end", filters.end);
    }

    if (page !== null) {
        params.set("page", page);
        params.set("page_size", filters.page_size);
    }

    return params;
}

function showError(message) {
    errorEl.textContent = message;
    errorEl.style.display = "block";
    statusEl.textContent = "Data Unavailable";
}

function updateSummary(summary) {
    document.getElementById("data-total").textContent =
        formatNumber(summary.total_candles, 0);

    document.getElementById("data-assets").textContent =
        summary.assets;

    document.getElementById("data-earliest").textContent =
        formatDate(summary.earliest);

    document.getElementById("data-latest").textContent =
        formatDate(summary.latest);
}

function updateTable(records) {
    tableBody.replaceChildren();

    if (!records.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 9;
        cell.textContent = "No matching candle records found.";

        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }

    records.forEach(record => {
        const row = document.createElement("tr");

        const values = [
            record.symbol,
            record.open_time,
            formatNumber(record.open, 6),
            formatNumber(record.high, 6),
            formatNumber(record.low, 6),
            formatNumber(record.close, 6),
            formatNumber(record.volume, 4),
            formatNumber(record.quote_volume, 2),
            formatNumber(record.trades, 0)
        ];

        values.forEach(value => {
            const cell = document.createElement("td");

            cell.textContent = value;
            row.appendChild(cell);
        });

        tableBody.appendChild(row);
    });
}

function updatePagination(pagination) {
    currentPage = pagination.page;
    totalPages = pagination.total_pages;

    const total = pagination.total_records;
    const pageSize = pagination.page_size;

    const start = total === 0
        ? 0
        : (currentPage - 1) * pageSize + 1;

    const end = Math.min(
        currentPage * pageSize,
        total
    );

    document.getElementById("pagination-info").textContent =
        `Showing ${start}-${end} of ${formatNumber(total, 0)} ` +
        `· Page ${currentPage} of ${totalPages}`;

    previousButton.disabled = currentPage <= 1;
    nextButton.disabled = currentPage >= totalPages;
}


async function loadData(page = 1) {
    const id = ++requestId;

    statusEl.textContent = "Loading...";
    errorEl.style.display = "none";

    previousButton.disabled = true;
    nextButton.disabled = true;

    const filters = activeFilters || getFilters();
    const params = createParams(filters, page);

    try {
        const response = await fetch(
            `/api/data?${params.toString()}`,
            { cache: "no-store" }
        );

        const result = await response.json();

        if (id !== requestId) return;

        if (!response.ok) {
            throw new Error(
                result.error || "Failed to load records"
            );
        }

        updateSummary(result.summary);
        updateTable(result.records);
        updatePagination(result.pagination);

        statusEl.textContent = "SQLite Connected";

    } catch (error) {
        if (id !== requestId) return;

        console.error("Data Explorer error:", error);
        showError(error.message);
    }
}


// Apply filters
document.getElementById("apply-filters")
    .addEventListener("click", () => {
        activeFilters = getFilters();
        loadData(1);
    });


// Reset filters
document.getElementById("reset-filters")
    .addEventListener("click", () => {
        symbolInput.value = "";
        startInput.value = "";
        endInput.value = "";
        pageSizeInput.value = "25";

        activeFilters = getFilters();
        loadData(1);
    });


// Pagination
previousButton.addEventListener("click", () => {
    if (currentPage > 1) {
        loadData(currentPage - 1);
    }
});

nextButton.addEventListener("click", () => {
    if (currentPage < totalPages) {
        loadData(currentPage + 1);
    }
});


// Export filtered records to CSV
exportButton.addEventListener("click", async () => {
    const filters = activeFilters || getFilters();
    const params = createParams(filters, null);

    exportButton.disabled = true;
    exportButton.textContent = "Preparing CSV...";

    try {
        const response = await fetch(
            `/api/data/export?${params.toString()}`
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(
                error.error || "CSV export failed"
            );
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = "cryptoscope_data.csv";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

    } catch (error) {
        showError(error.message);
    } finally {
        exportButton.disabled = false;
        exportButton.textContent = "↓ Export CSV";
    }
});


// Initial load
activeFilters = getFilters();
loadData(1);
