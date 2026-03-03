/*
 * Dashboard — fetches sensor data from API Gateway and draws simple line charts.
 */

// Read API Gateway URL from the HTML body data attribute
var API_URL = document.body.dataset.apiUrl;
var REFRESH_MS = parseInt(document.body.dataset.refreshInterval) * 1000;

// Sensor config
var SENSORS = {
    temperature: { label: "Temperature", unit: "°C", color: "#EF4444" },
    humidity: { label: "Humidity", unit: "%", color: "#3B82F6" },
    co2: { label: "CO₂", unit: "ppm", color: "#F59E0B" },
    pm25: { label: "Air Quality (PM2.5)", unit: "µg/m³", color: "#8B5CF6" }
};

var charts = {};

// ── Create one line chart per sensor ──
Object.keys(SENSORS).forEach(function (sensorType) {
    var config = SENSORS[sensorType];
    var ctx = document.getElementById("chart-" + sensorType);

    charts[sensorType] = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: config.label,
                data: [],
                borderColor: config.color,
                borderWidth: 2,
                pointRadius: 3,
                tension: 0.3,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: { display: true },
                y: { display: true, title: { display: true, text: config.unit } }
            }
        }
    });
});

// ── Fetch data and update charts ──
function updateCharts() {
    var hours = document.getElementById("timeRange").value;

    Object.keys(SENSORS).forEach(function (sensorType) {
        fetch(API_URL + "/api/sensor/" + sensorType + "?hours=" + hours)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                var chart = charts[sensorType];
                chart.data.labels = data.map(function (d) {
                    return new Date(d.timestamp).toLocaleTimeString();
                });
                chart.data.datasets[0].data = data.map(function (d) {
                    return d.avg_value;
                });
                chart.update();
            });
    });
}

// ── Fetch latest values for the summary cards ──
function updateCards() {
    fetch(API_URL + "/api/latest")
        .then(function (res) { return res.json(); })
        .then(function (data) {
            Object.keys(SENSORS).forEach(function (sensorType) {
                var reading = data[sensorType];
                if (!reading) return;

                document.getElementById("value-" + sensorType).textContent =
                    reading.avg_value.toFixed(1);

                var badge = document.getElementById("badge-" + sensorType);
                if (reading.anomaly) {
                    badge.textContent = "ANOMALY";
                    badge.className = "badge badge-pill badge-anomaly text-white";
                } else {
                    badge.textContent = "Normal";
                    badge.className = "badge badge-pill badge-normal text-white";
                }

                var t = new Date(reading.timestamp);
                document.getElementById("time-" + sensorType).textContent =
                    "Last: " + t.toLocaleTimeString();
            });
        });
}

// ── Clock ──
function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleTimeString();
}

// ── Start everything ──
updateCharts();
updateCards();
updateClock();
setInterval(updateCharts, REFRESH_MS);
setInterval(updateCards, REFRESH_MS);
setInterval(updateClock, 1000);
document.getElementById("timeRange").addEventListener("change", updateCharts);
