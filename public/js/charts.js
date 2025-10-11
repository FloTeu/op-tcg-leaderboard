/**
 * Minimal Chart.js wrapper for OP-TCG Leaderboard
 * Focus: Get line charts working with HTMX
 */

class ChartManager {
    constructor() {
        this.charts = new Map();
    }

    destroyChart(containerId) {
        // Clean up existing Chart.js instance
        const existingChart = Chart.getChart(containerId);
        if (existingChart) {
            existingChart.destroy();
        }
        
        // Clean up our tracking
        if (this.charts.has(containerId)) {
            this.charts.delete(containerId);
        }
    }

    destroyAll() {
        this.charts.forEach((chart, id) => {
            chart.destroy();
        });
        this.charts.clear();
    }

    createLineChart(config) {
        const {
            containerId,
            data,
            yKey = 'winRate',
            xKey = 'meta',
            ySuffix = '%',
            color = '#3B82F6',
            showXAxis = true,
            showYAxis = true
        } = config;

        // Clean up any existing chart first
        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas || !data || data.length === 0) {
            return null;
        }

        try {
            const chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: data.map(d => d[xKey]),
                    datasets: [{
                        data: data.map(d => d[yKey]),
                        borderColor: color,
                        backgroundColor: color,
                        tension: 0.3,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 2,
                        fill: false,
                        spanGaps: true,
                        segment: {
                            borderDash: ctx => {
                                // Use dashed line if either point is null/undefined
                                const p0 = ctx.p0.raw;
                                const p1 = ctx.p1.raw;
                                return (p0 === null || p0 === undefined || p1 === null || p1 === undefined) ? [6, 6] : undefined;
                            }
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false, // Disable animation to prevent HTMX conflicts
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.parsed.y + ySuffix;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: showXAxis,
                            grid: { display: false }
                        },
                        y: {
                            display: showYAxis,
                            grid: { display: showYAxis },
                            ticks: {
                                callback: function(value) {
                                    return value + ySuffix;
                                }
                            }
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;
            
        } catch (error) {
            console.error('Error creating line chart:', error);
            return null;
        }
    }

    createBarChart(config) {
        const {
            containerId,
            data,
            yKey = 'matches',
            xKey = 'meta',
            ySuffix = ' matches',
            color = '#3B82F6',
            showXAxis = true,
            showYAxis = true
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas || !data || data.length === 0) {
            return null;
        }

        try {
            const chart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: data.map(d => d[xKey]),
                    datasets: [{
                        data: data.map(d => d[yKey]),
                        backgroundColor: color,
                        borderColor: color,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.raw + ySuffix;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: showXAxis,
                            grid: { display: false }
                        },
                        y: {
                            display: showYAxis,
                            grid: { display: showYAxis },
                            beginAtZero: true
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;
            
        } catch (error) {
            console.error('Error creating bar chart:', error);
            return null;
        }
    }
}

// Global instance
window.chartManager = new ChartManager();

// HTMX integration - only destroy charts when the swap actually affects them
document.addEventListener('htmx:beforeSwap', function(event) {
    if (!window.chartManager) return;
    
    // Get the target element that will be swapped
    const swapTarget = event.detail.target || event.target;
    if (!swapTarget) return;
    
    // Check if any existing charts are inside the swap target
    const chartsToDestroy = [];
    window.chartManager.charts.forEach((chart, containerId) => {
        const chartCanvas = document.getElementById(containerId);
        if (chartCanvas && swapTarget.contains(chartCanvas)) {
            chartsToDestroy.push(containerId);
        }
    });
    
    // Only destroy charts that will actually be affected by the swap
    if (chartsToDestroy.length > 0) {
        console.log('HTMX swap will affect charts:', chartsToDestroy, 'in target:', swapTarget.id || swapTarget.className);
        chartsToDestroy.forEach(containerId => {
            window.chartManager.destroyChart(containerId);
        });
    }
});