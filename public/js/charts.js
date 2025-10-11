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

    createRadarChart(config) {
        const {
            containerId,
            data,
            leaderIds,
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'],
            showLegend = true
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas || !data || data.length === 0) {
            return null;
        }

        try {
            // Extract labels from first data object (excluding 'leader_id')
            const labels = Object.keys(data[0]).filter(key => key !== 'leader_id');

            // Prepare datasets for each leader
            const datasets = data.map((item, index) => ({
                label: item.leader_id,
                data: labels.map(label => item[label]),
                backgroundColor: colors[index] + '33', // Add transparency
                borderColor: colors[index],
                pointBackgroundColor: colors[index],
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: colors[index],
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }));

            const chart = new Chart(canvas, {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: {
                        legend: {
                            display: showLegend,
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                font: { size: 16 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.r + '%';
                                }
                            }
                        }
                    },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255, 255, 255, 0.2)' },
                            grid: { color: 'rgba(255, 255, 255, 0.2)' },
                            pointLabels: {
                                color: '#ffffff',
                                font: { size: 16 }
                            },
                            ticks: {
                                color: '#ffffff',
                                backdropColor: 'transparent'
                            }
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;
            
        } catch (error) {
            console.error('Error creating radar chart:', error);
            return null;
        }
    }

    createStreamChart(config) {
        const {
            containerId,
            data,
            yKey = 'wins',
            xKey = 'date',
            ySuffix = ' wins',
            color = '#10B981',
            showXAxis = true,
            showYAxis = true,
            tooltipBg = '#374151',
            tooltipBorder = '#6B7280'
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas || !data || data.length === 0) {
            return null;
        }

        try {
            // Get the chart context and create gradient
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, color);  // Start with full color
            gradient.addColorStop(1, color + '00'); // End with transparent

            // Create cumulative data for stream effect
            let cumulativeData = [];
            let runningTotal = 0;
            data.forEach(d => {
                runningTotal += d[yKey];
                cumulativeData.push(runningTotal);
            });

            // Format dates for display - shorter format
            const formatDate = (dateStr) => {
                const date = new Date(dateStr);
                const month = date.toLocaleDateString('en-US', { month: 'short' });
                const year = date.getFullYear().toString().slice(2); // Get last 2 digits of year
                return `${month} '${year}`;
            };

            // Group data points by month to avoid duplicate labels
            const monthLabels = new Map();
            data.forEach((d, i) => {
                const date = new Date(d[xKey]);
                const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
                if (!monthLabels.has(monthKey)) {
                    monthLabels.set(monthKey, i);
                }
            });

            // Define consistent colors for dark mode
            const COLORS = {
                BAR: '#9CA3AF',  // A medium gray that's visible but not too bright
                BAR_BORDER: '#D1D5DB',  // Slightly lighter gray for bar borders
                AXIS_TEXT: '#E5E7EB',  // Light gray for axis text
                GRID: 'rgba(255, 255, 255, 0.1)'  // Subtle grid lines
            };

            // Find max values for scaling
            const maxWins = Math.max(...data.map(d => d[yKey]));
            const maxCumulative = Math.max(...cumulativeData);

            const chart = new Chart(canvas, {
                data: {
                    labels: data.map(d => formatDate(d[xKey])),
                    datasets: [
                        // Bar chart for individual wins
                        {
                            type: 'bar',
                            data: data.map(d => d[yKey]),
                            backgroundColor: COLORS.BAR,
                            borderColor: COLORS.BAR_BORDER,
                            borderWidth: 1,
                            barPercentage: 0.4,
                            order: 2,
                            yAxisID: 'y-axis-bars',
                            barThickness: 'flex',
                            minBarLength: 10
                        },
                        // Line chart for cumulative wins
                        {
                            type: 'line',
                            data: cumulativeData,
                            borderColor: color,
                            backgroundColor: gradient,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 2,
                            pointHoverRadius: 4,
                            borderWidth: 2,
                            pointStyle: 'circle',
                            pointBackgroundColor: color,
                            pointBorderColor: '#fff',
                            order: 1,
                            yAxisID: 'y-axis-line'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false, // Disabled for HTMX compatibility
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: tooltipBorder,
                            borderWidth: 1,
                            padding: 8,
                            displayColors: false,
                            callbacks: {
                                title: function(context) {
                                    return data[context[0].dataIndex][xKey];
                                },
                                label: function(context) {
                                    if (context.datasetIndex === 0) {
                                        return 'Wins on this day: ' + context.parsed.y + ySuffix;
                                    } else {
                                        return 'Total wins: ' + context.parsed.y + ySuffix;
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: showXAxis,
                            grid: { display: false },
                            ticks: {
                                color: COLORS.AXIS_TEXT,
                                font: { size: 10 },
                                maxRotation: 0,
                                minRotation: 0,
                                padding: 8,
                                autoSkip: false,
                                callback: function(value, index) {
                                    const date = new Date(data[index][xKey]);
                                    const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
                                    return monthLabels.get(monthKey) === index ? this.getLabelForValue(value) : '';
                                }
                            }
                        },
                        'y-axis-bars': {
                            display: showYAxis,
                            position: 'left',
                            grid: { display: false },
                            ticks: {
                                color: COLORS.AXIS_TEXT,
                                font: { size: 10 },
                                padding: 5,
                                callback: function(value) {
                                    return value + ySuffix;
                                },
                                stepSize: 1
                            },
                            min: 0,
                            max: Math.max(maxWins * 1.2, 4),
                            border: { color: COLORS.BAR_BORDER }
                        },
                        'y-axis-line': {
                            display: showYAxis,
                            position: 'right',
                            grid: {
                                display: showYAxis,
                                color: COLORS.GRID
                            },
                            ticks: {
                                color: COLORS.AXIS_TEXT,
                                font: { size: 10 },
                                padding: 5,
                                callback: function(value) {
                                    return value + ySuffix;
                                }
                            },
                            min: 0,
                            max: Math.ceil(maxCumulative * 1.1),
                            border: { color: COLORS.BAR_BORDER }
                        }
                    },
                    layout: {
                        padding: {
                            top: 20,
                            right: 30,
                            bottom: 20,
                            left: 30
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;
            
        } catch (error) {
            console.error('Error creating stream chart:', error);
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