// Student Academic Performance Monitoring and Prediction System
// Dashboard Script & Chart Helpers

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');

    if (sidebarToggle && sidebar && backdrop) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
            backdrop.classList.toggle('show');
        });

        backdrop.addEventListener('click', function () {
            sidebar.classList.remove('show');
            backdrop.classList.remove('show');
        });
    }

    // 2. Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 3. Table filter helper if input with data-table-filter exists
    const tableFilterInputs = document.querySelectorAll('[data-table-filter]');
    tableFilterInputs.forEach(function (input) {
        input.addEventListener('keyup', function () {
            const targetTableId = this.getAttribute('data-table-filter');
            const targetTable = document.getElementById(targetTableId);
            if (!targetTable) return;
            const filterValue = this.value.toLowerCase();
            const rows = targetTable.querySelectorAll('tbody tr');

            rows.forEach(function (row) {
                const text = row.textContent.toLowerCase();
                if (text.indexOf(filterValue) > -1) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
});

// Chart.js Palette
const ChartColors = {
    navy: '#0f2744',
    secondaryNavy: '#1a365d',
    teal: '#0d9488',
    tealLight: '#14b8a6',
    amber: '#f59e0b',
    red: '#ef4444',
    green: '#10b981',
    purple: '#8b5cf6',
    blue: '#3b82f6',
    slate: '#94a3b8'
};

// Helper: Bar Chart
function renderBarChart(canvasId, labels, data, labelName, bgColor) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: labelName,
                data: data,
                backgroundColor: bgColor || ChartColors.teal,
                borderRadius: 6,
                maxBarThickness: 45
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f1f5f9' },
                    ticks: { callback: v => v + '%' }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.raw}%`
                    }
                }
            }
        }
    });
}

// Helper: Doughnut / Pie Chart
function renderDoughnutChart(canvasId, labels, data, bgColors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: bgColors || [ChartColors.green, ChartColors.blue, ChartColors.amber, ChartColors.red],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 } }
                }
            }
        }
    });
}

// Helper: Line Chart
function renderLineChart(canvasId, labels, data, labelName) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: labelName,
                data: data,
                borderColor: ChartColors.teal,
                backgroundColor: 'rgba(13, 148, 136, 0.1)',
                borderWidth: 3,
                tension: 0.35,
                fill: true,
                pointBackgroundColor: ChartColors.secondaryNavy,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f1f5f9' },
                    ticks: { callback: v => v + '%' }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
