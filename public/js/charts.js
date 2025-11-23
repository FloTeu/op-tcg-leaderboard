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

    createBubbleChart(config) {
        const {
            containerId,
            data,
            colors,
            title = 'Leader Tournament Popularity',
            tooltipBg = '#374151',
            tooltipBorder = '#6B7280',
            tickTextColor = '#E5E7EB'
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas || !data || data.length === 0) {
            return null;
        }

        try {
            // Clean up old tooltip if it exists
            const oldTooltip = document.getElementById('chartjs-tooltip');
            if (oldTooltip) {
                oldTooltip.remove();
            }

            // Clean up old chart event listeners using a stable reference
            if (window.bubbleChartHideTooltipHandler) {
                try { 
                    document.removeEventListener('mouseout', window.bubbleChartHideTooltipHandler); 
                } catch (e) {}
            }

            function hideTooltip() {
                const tooltipEl = document.getElementById('chartjs-tooltip');
                if (tooltipEl) {
                    tooltipEl.style.opacity = 0;
                }
            }

            // Add global mouse out listener to hide tooltip when mouse leaves chart area
            window.bubbleChartHideTooltipHandler = hideTooltip;
            document.addEventListener('mouseout', window.bubbleChartHideTooltipHandler);

            // Clear the canvas and reset its size
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Reset canvas size to match container
            const containerElement = canvas.parentElement;
            if (containerElement) {
                canvas.width = containerElement.clientWidth;
                canvas.height = containerElement.clientHeight;
            }

            // Store multi-color data for custom drawing
            const multiColorData = colors.map((colorData, index) => {
                if (Array.isArray(colorData) && colorData.length > 1) {
                    return {
                        isMultiColor: true,
                        colors: colorData,
                        dataIndex: index
                    };
                }
                return {
                    isMultiColor: false,
                    colors: [Array.isArray(colorData) ? colorData[0] : colorData],
                    dataIndex: index
                };
            });

            // Process colors for Chart.js (use first color for multi-color leaders)
            const processedColors = colors.map((colorData, index) => {
                if (Array.isArray(colorData) && colorData.length > 1) {
                    // Multi-color leader - use first color as base (will be overdrawn by plugin)
                    const color = colorData[0];
                    const r = parseInt(color.slice(1,3), 16);
                    const g = parseInt(color.slice(3,5), 16);
                    const b = parseInt(color.slice(5,7), 16);
                    return `rgba(${r},${g},${b},0.7)`;
                } else {
                    // Single color leader - add transparency
                    const color = Array.isArray(colorData) ? colorData[0] : colorData;
                    const r = parseInt(color.slice(1,3), 16);
                    const g = parseInt(color.slice(3,5), 16);
                    const b = parseInt(color.slice(5,7), 16);
                    return `rgba(${r},${g},${b},0.7)`;
                }
            });

            // Process hover colors for multi-color support (slightly more opaque)
            const processedHoverColors = colors.map((colorData, index) => {
                if (Array.isArray(colorData) && colorData.length > 1) {
                    // Multi-color leader - use first color but more opaque
                    const color = colorData[0];
                    const r = parseInt(color.slice(1,3), 16);
                    const g = parseInt(color.slice(3,5), 16);
                    const b = parseInt(color.slice(5,7), 16);
                    return `rgba(${r},${g},${b},0.9)`;
                } else {
                    // Single color leader - more opaque on hover
                    const color = Array.isArray(colorData) ? colorData[0] : colorData;
                    const r = parseInt(color.slice(1,3), 16);
                    const g = parseInt(color.slice(3,5), 16);
                    const b = parseInt(color.slice(5,7), 16);
                    return `rgba(${r},${g},${b},0.9)`; // More opaque on hover
                }
            });

            // Process border colors (use first color for multi-color leaders)
            const borderColors = colors.map(colorData => {
                return Array.isArray(colorData) ? colorData[0] : colorData;
            });

            // Custom plugin to draw multi-color segments
            const multiColorPlugin = {
                id: 'multiColorBubbles',
                afterDatasetsDraw: function(chart) {
                    const ctx = chart.ctx;
                    const meta = chart.getDatasetMeta(0);

                    meta.data.forEach((element, index) => {
                        const colorInfo = multiColorData[index];
                        if (colorInfo && colorInfo.isMultiColor && colorInfo.colors.length > 1) {
                            const model = element;
                            const x = model.x;
                            const y = model.y;
                            const radius = model.options.radius;

                            // Draw pie-like segments within the bubble
                            const colors = colorInfo.colors;
                            const angleStep = (2 * Math.PI) / colors.length;

                            ctx.save();

                            colors.forEach((color, colorIndex) => {
                                ctx.beginPath();
                                ctx.moveTo(x, y);

                                const startAngle = colorIndex * angleStep;
                                const endAngle = (colorIndex + 1) * angleStep;

                                ctx.arc(x, y, radius, startAngle, endAngle);
                                ctx.closePath();

                                // Parse color and add transparency
                                const r = parseInt(color.slice(1,3), 16);
                                const g = parseInt(color.slice(3,5), 16);
                                const b = parseInt(color.slice(5,7), 16);
                                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.7)`;
                                ctx.fill();

                                // Add subtle border
                                ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
                                ctx.lineWidth = 0.5;
                                ctx.stroke();
                            });

                            ctx.restore();
                        }
                    });
                }
            };

            const chart = new Chart(canvas, {
                type: 'bubble',
                data: {
                    datasets: [{
                        data: data,
                        backgroundColor: processedColors,
                        borderColor: borderColors,
                        borderWidth: 1,
                        hoverBackgroundColor: processedHoverColors,
                        radius: (context) => {
                            // Get the bubble size from the data
                            return context.raw.r;
                        }
                    }]
                },
                plugins: [multiColorPlugin],
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false, // Disabled for HTMX compatibility
                    layout: {
                        padding: {
                            top: 20,
                            right: 20,
                            bottom: 50,  // Increased bottom padding to show x-axis properly
                            left: window.innerWidth > 768 ? 50 : 30
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: title,
                            color: 'white',
                            font: { size: 16 },
                            padding: { bottom: 10 }
                        },
                        legend: { display: false },
                        tooltip: { enabled: false }  // Disable default tooltip
                    },
                    hover: {
                        mode: 'nearest',
                        intersect: true
                    },
                    events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
                    onHover: function(event, chartElements) {
                        let tooltipEl = document.getElementById('chartjs-tooltip');

                        if (!tooltipEl) {
                            const div = document.createElement('div');
                            div.id = 'chartjs-tooltip';
                            div.style.position = 'absolute';
                            div.style.pointerEvents = 'none';
                            div.style.opacity = '0';
                            div.style.transition = 'all .1s ease';
                            document.body.appendChild(div);
                            tooltipEl = div;
                        }

                        if (!chartElements || chartElements.length === 0) {
                            if (tooltipEl) {
                                tooltipEl.style.opacity = 0;
                            }
                            return;
                        }

                        const element = chartElements[0];
                        const data = element.element.$context.raw;
                        const dataIndex = element.index;
                        const leaderColors = colors[dataIndex];

                        // Create color indicators for multi-color leaders
                        const colorIndicators = Array.isArray(leaderColors) && leaderColors.length > 1
                            ? leaderColors.map(color => `<span style="display: inline-block; width: 12px; height: 12px; background-color: ${color}; margin-right: 4px; border-radius: 2px;"></span>`).join('')
                            : '';

                        // Create tooltip content with responsive layout
                        const isMobile = window.innerWidth <= 768;
                        const tooltipContent = `
                            <div style="
                                display: flex;
                                gap: ${isMobile ? '8px' : '16px'};
                                min-width: ${isMobile ? '280px' : '400px'};
                                height: ${isMobile ? '120px' : '150px'};
                                padding: 0;
                            ">
                                <div style="
                                    flex: 0 0 30%;
                                    height: 100%;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    overflow: hidden;
                                    padding: 0;
                                    margin: 0;
                                ">
                                    ${data.image ? `<img src="${data.image}" style="width: 100%; height: 100%; object-fit: contain; display: block;">` : ''}
                                </div>
                                <div style="
                                    flex: 0 0 70%;
                                    padding: ${isMobile ? '8px 12px 8px 0' : '12px 16px 12px 0'};
                                    display: flex;
                                    flex-direction: column;
                                    justify-content: center;
                                ">
                                    <div style="font-weight: bold; margin-bottom: ${isMobile ? '8px' : '12px'}; font-size: ${isMobile ? '1em' : '1.2em'}; white-space: normal;">${data.name}</div>
                                    <div style="margin: ${isMobile ? '2px' : '4px'} 0; font-size: ${isMobile ? '0.9em' : '1em'};">Win Rate: ${(data.y * 100).toFixed(1)}%</div>
                                    <div style="margin: ${isMobile ? '2px' : '4px'} 0; font-size: ${isMobile ? '0.9em' : '1em'};">Tournament Matches: ${data.x}</div>
                                    <div style="margin: ${isMobile ? '2px' : '4px'} 0; font-size: ${isMobile ? '0.9em' : '1em'};">Tournament Wins: ${data.raw_wins}</div>
                                    ${colorIndicators ? `<div style="margin: ${isMobile ? '6px' : '8px'} 0 ${isMobile ? '2px' : '4px'} 0; font-size: ${isMobile ? '0.85em' : '0.9em'};"><strong>Colors:</strong></div><div style="margin: ${isMobile ? '2px' : '4px'} 0;">${colorIndicators}</div>` : ''}
                                </div>
                            </div>
                        `;

                        tooltipEl.innerHTML = tooltipContent;
                        tooltipEl.style.opacity = 1;
                        tooltipEl.style.position = 'absolute';
                        tooltipEl.style.backgroundColor = tooltipBg;
                        tooltipEl.style.color = '#ffffff';
                        tooltipEl.style.borderRadius = '4px';
                        tooltipEl.style.border = '1px solid ' + tooltipBorder;
                        tooltipEl.style.pointerEvents = 'none';
                        tooltipEl.style.zIndex = 9999;
                        tooltipEl.style.transform = 'translate(-50%, -100%)';
                        tooltipEl.style.transition = 'all .1s ease';
                        tooltipEl.style.padding = '0';
                        tooltipEl.style.overflow = 'hidden';

                        // Position the tooltip safely
                        try {
                            const chartRect = canvas.getBoundingClientRect();
                            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

                            // Try multiple methods to get element position
                            let x, y;
                            if (element.element && element.element.tooltipPosition) {
                                const position = element.element.tooltipPosition();
                                x = position.x;
                                y = position.y;
                            } else if (element.element && element.element.x !== undefined) {
                                x = element.element.x;
                                y = element.element.y;
                            } else {
                                // Fallback to chart center
                                x = chartRect.width / 2;
                                y = chartRect.height / 2;
                            }

                            if (x !== undefined && y !== undefined && tooltipEl) {
                                tooltipEl.style.left = (chartRect.left + scrollLeft + x) + 'px';
                                tooltipEl.style.top = (chartRect.top + scrollTop + y - 10) + 'px';
                            }
                        } catch (error) {
                            console.warn('Error positioning tooltip:', error);
                            if (tooltipEl) {
                                tooltipEl.style.opacity = 0;
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'logarithmic',
                            display: true,  // Always show x-axis
                            title: {
                                display: window.innerWidth > 768,  // Hide title on mobile, but show axis
                                text: 'Number of Tournament Matches',
                                color: 'white',
                                font: {
                                    size: window.innerWidth > 768 ? 12 : 10
                                }
                            },
                            ticks: {
                                display: true,  // Always show ticks
                                color: tickTextColor,
                                font: {
                                    size: window.innerWidth > 768 ? 10 : 8
                                },
                                padding: window.innerWidth > 768 ? 5 : 2,
                                maxTicksLimit: window.innerWidth > 768 ? 8 : 5,  // Fewer ticks on mobile
                                maxRotation: 0,  // Prevent label rotation on mobile
                                minRotation: 0
                            },
                            grid: {
                                display: true,  // Always show grid
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            display: true,  // Always show y-axis
                            title: {
                                display: window.innerWidth > 768,  // Hide title on mobile, but show axis
                                text: 'Win Rate',
                                color: 'white',
                                font: {
                                    size: window.innerWidth > 768 ? 12 : 10
                                }
                            },
                            ticks: {
                                display: true,  // Always show ticks
                                color: tickTextColor,
                                font: {
                                    size: window.innerWidth > 768 ? 10 : 8
                                },
                                padding: window.innerWidth > 768 ? 5 : 2,
                                maxTicksLimit: window.innerWidth > 768 ? 8 : 5,  // Fewer ticks on mobile
                                callback: function(value) {
                                    return (value * 100).toFixed(0) + '%';
                                }
                            },
                            grid: {
                                display: true,  // Always show grid
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;
            
        } catch (error) {
            console.error('Error creating bubble chart:', error);
            return null;
        }
    }

    createPriceDevelopmentChart(config) {
        const {
            containerId,
            data,
            cardName
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas) {
            console.error('Chart container not found:', containerId);
            return null;
        }

        try {
            // Clear the canvas completely
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Reset canvas size to container
            const containerElement = canvas.parentElement;
            if (containerElement) {
                canvas.width = containerElement.clientWidth;
                canvas.height = containerElement.clientHeight;
            }

            // Prepare datasets
            const datasets = [];

            // EUR dataset
            const eurData = data.map(d => d.eur_price);
            if (eurData.some(price => price !== null && price !== undefined)) {
                datasets.push({
                    label: 'EUR (€)',
                    data: eurData,
                    borderColor: '#10B981', // Emerald green
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderWidth: 2,
                    spanGaps: true,
                    segment: {
                        borderDash: ctx => !ctx.p0.raw || !ctx.p1.raw ? [6, 6] : undefined
                    },
                    pointStyle: 'circle',
                    pointBackgroundColor: eurData.map(price => price === null ? 'transparent' : '#10B981'),
                    pointBorderColor: eurData.map(price => price === null ? '#10B981' : '#10B981')
                });
            }

            // USD dataset
            const usdData = data.map(d => d.usd_price);
            if (usdData.some(price => price !== null && price !== undefined)) {
                datasets.push({
                    label: 'USD ($)',
                    data: usdData,
                    borderColor: '#3B82F6', // Blue
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderWidth: 2,
                    spanGaps: true,
                    segment: {
                        borderDash: ctx => !ctx.p0.raw || !ctx.p1.raw ? [6, 6] : undefined
                    },
                    pointStyle: 'circle',
                    pointBackgroundColor: usdData.map(price => price === null ? 'transparent' : '#3B82F6'),
                    pointBorderColor: usdData.map(price => price === null ? '#3B82F6' : '#3B82F6')
                });
            }

            const chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 300
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#E5E7EB',
                                font: {
                                    size: 12
                                },
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 20,
                                boxWidth: 10,
                                boxHeight: 10
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: '#374151',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                title: function(context) {
                                    return 'Date: ' + context[0].label;
                                },
                                label: function(context) {
                                    const value = context.parsed.y;
                                    if (value === null || value === undefined) {
                                        return context.dataset.label + ': No data';
                                    }
                                    const currency = context.dataset.label.includes('eur') ? '€' : '$';
                                    return context.dataset.label + ': ' + currency + value.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: {
                                display: true,
                                color: 'rgba(75, 85, 99, 0.3)'
                            },
                            ticks: {
                                color: '#9CA3AF',
                                font: {
                                    size: 11
                                },
                                maxRotation: 45,
                                minRotation: 0,
                                padding: 8,
                                maxTicksLimit: 8
                            }
                        },
                        y: {
                            display: true,
                            grid: {
                                display: true,
                                color: 'rgba(75, 85, 99, 0.2)'
                            },
                            ticks: {
                                color: '#9CA3AF',
                                font: {
                                    size: 11
                                },
                                padding: 8,
                                callback: function(value, index, values) {
                                    return '€/' + value.toFixed(2);
                                }
                            },
                            beginAtZero: true
                        }
                    },
                    layout: {
                        padding: {
                            top: 10,
                            right: 15,
                            bottom: 10,
                            left: 15
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;

        } catch (error) {
            console.error('Error creating price development chart:', error);
            return null;
        }
    }

    createCardOccurrenceChart(config) {
        const {
            containerId,
            data,
            metaFormats,
            leaders,
            colors,
            isNormalized,
            cardName
        } = config;

        this.destroyChart(containerId);

        const canvas = document.getElementById(containerId);
        if (!canvas) {
            console.error('Chart container not found:', containerId);
            return null;
        }

        try {
            // Clean up any existing tooltips
            const oldTooltips = document.querySelectorAll('#chartjs-tooltip');
            oldTooltips.forEach(tooltip => tooltip.remove());

            // Clear the canvas completely
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Create datasets for each leader
            const datasets = leaders.map((leader, index) => {
                const leaderData = data.map(meta => meta[leader] || 0);

                return {
                    label: leader,
                    data: leaderData,
                    borderColor: colors[index],
                    backgroundColor: colors[index] + (isNormalized ? '60' : '40'), // More opacity for stacked areas
                    fill: isNormalized ? (index === 0 ? 'origin' : '-1') : true, // Proper stacking: fill to previous dataset
                    tension: isNormalized ? 0.2 : 0.4, // Less curve for normalized to avoid overlap appearance
                    pointRadius: isNormalized ? 2 : 3,
                    pointHoverRadius: isNormalized ? 4 : 5,
                    borderWidth: isNormalized ? 1 : 2,
                    stack: isNormalized ? 'Stack 0' : undefined // Enable stacking for normalized mode
                };
            });

            const chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: metaFormats,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 800,
                        easing: 'easeInOutQuart'
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#9CA3AF',
                                font: {
                                    size: 11
                                },
                                maxRotation: 45,
                                minRotation: 0,
                                padding: 8
                            }
                        },
                        y: {
                            display: true,
                            stacked: isNormalized,  // Enable stacking for normalized mode
                            grid: {
                                display: true,
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#9CA3AF',
                                font: {
                                    size: 11
                                },
                                padding: 8,
                                // Only set stepSize for normalized mode to avoid excessive tick generation
                                ...(isNormalized && { stepSize: 0.1 }),
                                callback: function(value) {
                                    if (isNormalized) {
                                        return (value * 100).toFixed(1) + '%';
                                    } else {
                                        // For absolute values, show whole numbers
                                        return Math.round(value);
                                    }
                                }
                            },
                            beginAtZero: true,
                            max: isNormalized ? 1 : undefined
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: '#E5E7EB',
                                font: {
                                    size: 10
                                },
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 15,
                                boxWidth: 8,
                                boxHeight: 8
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: '#374151',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                title: function(context) {
                                    return 'Meta Format: ' + context[0].label;
                                },
                                label: function(context) {
                                    const value = context.parsed.y;
                                    if (isNormalized) {
                                        return context.dataset.label + ': ' + (value * 100).toFixed(1) + '%';
                                    } else {
                                        return context.dataset.label + ': ' + value + ' occurrences';
                                    }
                                }
                            }
                        }
                    },
                    layout: {
                        padding: {
                            top: 10,
                            right: 10,
                            bottom: 60, // Increased bottom padding for legend
                            left: 10
                        }
                    }
                }
            });

            this.charts.set(containerId, chart);
            return chart;

        } catch (error) {
            console.error('Error creating card occurrence chart:', error);
            return null;
        }
    }

 //    createDonutChart(config) {
//        const {
//            containerId,
//            labels,
//            values,
//            colors,
//            images = [],
//            leaderIds = null,
//            tooltipBg = '#374151',
//            tooltipBorder = '#6B7280'
//        } = config;
//
//        this.destroyChart(containerId);
//
//        const canvas = document.getElementById(containerId);
//        if (!canvas || !labels || labels.length === 0) {
//            return null;
//        }
//
//        try {
//            // Clear canvas completely
//            const ctx = canvas.getContext('2d');
//            ctx.clearRect(0, 0, canvas.width, canvas.height);
//
//            // Reset canvas size to container
//            const container = canvas.parentElement;
//            if (container) {
//                canvas.width = container.clientWidth;
//                canvas.height = container.clientHeight;
//            }
//
//            const total = (Array.isArray(values) ? values : []).reduce((a,b)=>a+(+b||0),0) || 1;
//            const actualLeaderIds = leaderIds || labels;
//
//            // Store multi-color data for custom drawing
//            const multiColorData = colors.map((colorData, index) => {
//                if (Array.isArray(colorData) && colorData.length > 1) {
//                    return {
//                        isMultiColor: true,
//                        colors: colorData,
//                        dataIndex: index
//                    };
//                }
//                return {
//                    isMultiColor: false,
//                    colors: [Array.isArray(colorData) ? colorData[0] : colorData],
//                    dataIndex: index
//                };
//            });
//
//            const data = {
//                labels: labels,
//                datasets: [{
//                    data: values,
//                    backgroundColor: function(ctx) {
//                        try {
//                            const idx = ctx.dataIndex;
//                            const colorData = colors[idx];
//                            // Single color: return the color directly
//                            if (!Array.isArray(colorData) || colorData.length <= 1) {
//                                return Array.isArray(colorData) ? colorData[0] : colorData;
//                            }
//                            // Multi color: build conic gradient aligned to the arc
//                            const el = ctx.chart.getDatasetMeta(0).data[idx];
//                            if (!el) return 'rgba(0,0,0,0)';
//
//                            // Get arc properties - try multiple methods to ensure we get valid values
//                            let x, y, startAngle, endAngle;
//
//                            if (el.getProps) {
//                                // Try animated properties first
//                                const props = el.getProps(['x','y','startAngle','endAngle'], true);
//                                if (props && props.x != null) {
//                                    x = props.x;
//                                    y = props.y;
//                                    startAngle = props.startAngle;
//                                    endAngle = props.endAngle;
//                                }
//                            }
//
//                            // Fallback to static properties if needed
//                            if (x == null) {
//                                x = el.x;
//                                y = el.y;
//                                startAngle = el.startAngle;
//                                endAngle = el.endAngle;
//                            }
//
//                            // Final fallback to chart center
//                            if (x == null) {
//                                const chartArea = ctx.chart.chartArea;
//                                x = (chartArea.left + chartArea.right) / 2;
//                                y = (chartArea.top + chartArea.bottom) / 2;
//                                startAngle = 0;
//                                endAngle = Math.PI * 2;
//                            }
//
//                            const totalAngle = Math.max(1e-6, endAngle - startAngle);
//                            const grad = ctx.chart.ctx.createConicGradient(startAngle, x, y);
//                            const step = totalAngle / colorData.length;
//
//                            for (let i=0; i<colorData.length; i++) {
//                                const start = (i*step) / (Math.PI*2);
//                                const end = ((i+1)*step) / (Math.PI*2);
//                                const col = colorData[i];
//                                grad.addColorStop(start, col);
//                                grad.addColorStop(end, col);
//                            }
//                            return grad;
//                        } catch (e) {
//                            return 'rgba(0,0,0,0)';
//                        }
//                    },
//                    borderColor: 'transparent', // Remove grey borders for cleaner look
//                    borderWidth: 0, // No borders
//                    hoverBackgroundColor: function(ctx) {
//                        try {
//                            const idx = ctx.dataIndex;
//                            const colorData = colors[idx];
//                            // Single color: brighten a bit
//                            if (!Array.isArray(colorData) || colorData.length <= 1) {
//                                const base = Array.isArray(colorData) ? colorData[0] : colorData;
//                                const r = parseInt(base.slice(1,3),16), g = parseInt(base.slice(3,5),16), b = parseInt(base.slice(5,7),16);
//                                const br = Math.min(255, Math.round(r*1.1)), bg = Math.min(255, Math.round(g*1.1)), bb = Math.min(255, Math.round(b*1.1));
//                                return `rgb(${br}, ${bg}, ${bb})`;
//                            }
//                            // Multi color: brighten each stop
//                            const el = ctx.chart.getDatasetMeta(0).data[idx];
//                            if (!el || !el.getProps) return 'rgba(0,0,0,0)';
//                            const props = el.getProps(['x','y','startAngle','endAngle'], true);
//                            const totalAngle = Math.max(1e-6, props.endAngle - props.startAngle);
//                            const grad = ctx.chart.ctx.createConicGradient(props.startAngle, props.x, props.y);
//                            const step = totalAngle / colorData.length;
//                            for (let i=0; i<colorData.length; i++) {
//                                const start = (i*step) / (Math.PI*2);
//                                const end = ((i+1)*step) / (Math.PI*2);
//                                const base = colorData[i];
//                                const r = parseInt(base.slice(1,3),16), g = parseInt(base.slice(3,5),16), b = parseInt(base.slice(5,7),16);
//                                const br = Math.min(255, Math.round(r*1.1)), bg = Math.min(255, Math.round(g*1.1)), bb = Math.min(255, Math.round(b*1.1));
//                                const col = `rgb(${br}, ${bg}, ${bb})`;
//                                grad.addColorStop(start, col);
//                                grad.addColorStop(end, col);
//                            }
//                            return grad;
//                        } catch (e) {
//                            return 'rgba(0,0,0,0)';
//                        }
//                    },
//                    hoverBorderColor: 'transparent', // No border on hover
//                    hoverBorderWidth: 0, // No border thickness
//                    hoverOffset: 8, // Native bounce for all segments
//                    spacing: 4, // Increased spacing between segments for natural separation
//                    borderRadius: 8, // Rounded edges for modern look
//                    borderSkipped: false // Ensure all edges are rounded
//                }]
//            };
//
//            const chart = new Chart(ctx, {
//                type: 'doughnut',
//                data,
//                options: {
//                    responsive: true,
//                    maintainAspectRatio: false,
//                    layout: {
//                        padding: 30  // More padding for better visual breathing room
//                    },
//                    elements: {
//                        arc: {
//                            borderWidth: 0, // Ensure no borders on arcs
//                            borderRadius: 8, // Rounded corners for individual segments
//                            borderSkipped: false // Ensure all edges are rounded
//                        }
//                    },
//                    animation: {
//                        duration: 300,
//                        easing: 'easeOutQuart' // Smooth animation curve
//                    },
//                    plugins: {
//                        legend: { display: false },
//                        tooltip: { enabled: false }  // Disable default tooltip, use custom one
//                    },
//                    hover: {
//                        mode: 'nearest',
//                        intersect: true,
//                        animationDuration: 200 // Match Chart.js default for consistency
//                    },
//                    events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
//                    onClick: function(event, chartElements) {
//                        if (chartElements && chartElements.length > 0) {
//                            const element = chartElements[0];
//                            const dataIndex = element.index;
//                            const leaderId = actualLeaderIds[dataIndex]; // Use the actual leader ID
//
//                            // Get current filter values from the page
//                            const metaFormat = document.querySelector('[name="meta_format"]')?.value || '';
//                            const region = document.querySelector('[name="region"]')?.value || '';
//                            const days = document.querySelector('[name="days"]')?.value || '14';
//                            const placing = document.querySelector('[name="placing"]')?.value || 'all';
//
//                            // Build URL with all current filters
//                            const params = new URLSearchParams();
//                            params.set('lid', leaderId);
//                            if (metaFormat) params.set('meta_format', metaFormat);
//                            if (region) params.set('region', region);
//                            params.set('days', days);
//                            params.set('placing', placing);
//
//                            // Open decklist modal with tournament filters
//                            htmx.ajax('GET', '/api/decklist-modal?' + params.toString(), {
//                                target: 'body',
//                                swap: 'beforeend'
//                            });
//                        }
//                    },
//                    onHover: function(event, chartElements) {
//                        let tooltipEl = document.getElementById('chartjs-tooltip');
//
//                        if (!tooltipEl) {
//                            const div = document.createElement('div');
//                            div.id = 'chartjs-tooltip';
//                            div.style.position = 'absolute';
//                            div.style.pointerEvents = 'none';
//                            div.style.opacity = '0';
//                            div.style.transition = 'all .1s ease';
//                            document.body.appendChild(div);
//                            tooltipEl = div;
//                        }
//
//                        if (!chartElements || chartElements.length === 0) {
//                            if (tooltipEl) {
//                                tooltipEl.style.opacity = 0;
//                            }
//                            return;
//                        }
//
//                        const element = chartElements[0];
//                        const dataIndex = element.index;
//                        const label = labels[dataIndex];
//                        const value = values[dataIndex];
//                        const image = images && images[dataIndex] ? images[dataIndex] : '';
//                        const pct = ((value/total)*100).toFixed(1);
//                        const leaderColors = colors[dataIndex];
//
//                        // Create color indicators for multi-color leaders
//                        const colorIndicators = Array.isArray(leaderColors) && leaderColors.length > 1
//                            ? leaderColors.map(color => `<span style="display: inline-block; width: 12px; height: 12px; background-color: ${color}; margin-right: 4px; border-radius: 2px;"></span>`).join('')
//                            : '';
//
//                        // Create tooltip content with flex layout
//                        const tooltipContent = `
//                            <div style="
//                                display: flex;
//                                gap: 16px;
//                                min-width: 300px;
//                                height: 120px;
//                                padding: 0;
//                            ">
//                                <div style="
//                                    flex: 0 0 30%;
//                                    height: 100%;
//                                    display: flex;
//                                    align-items: center;
//                                    justify-content: center;
//                                    overflow: hidden;
//                                    padding: 0;
//                                    margin: 0;
//                                ">
//                                    ${image ? `<img src="${image}" style="width: 100%; height: 100%; object-fit: contain; display: block;">` : ''}
//                                </div>
//                                <div style="
//                                    flex: 0 0 70%;
//                                    padding: 12px 16px 12px 0;
//                                    display: flex;
//                                    flex-direction: column;
//                                    justify-content: center;
//                                ">
//                                    <div style="font-weight: bold; margin-bottom: 12px; font-size: 1.2em; white-space: normal;">${label}</div>
//                                    <div style="margin: 4px 0;">Count: ${value}</div>
//                                    <div style="margin: 4px 0;">Percentage: ${pct}%</div>
//                                    ${colorIndicators ? `<div style="margin: 8px 0 4px 0;"><strong>Colors:</strong></div><div style="margin: 4px 0;">${colorIndicators}</div>` : ''}
//                                </div>
//                            </div>
//                        `;
//
//                        tooltipEl.innerHTML = tooltipContent;
//                        tooltipEl.style.opacity = 1;
//                        tooltipEl.style.backgroundColor = tooltipBg;
//                        tooltipEl.style.color = '#ffffff';
//                        tooltipEl.style.borderRadius = '4px';
//                        tooltipEl.style.border = '1px solid ' + tooltipBorder;
//                        tooltipEl.style.zIndex = 9999;
//                        tooltipEl.style.transform = 'translate(-50%, -100%)';
//                        tooltipEl.style.padding = '0';
//                        tooltipEl.style.overflow = 'hidden';
//
//                        // Position the tooltip
//                        try {
//                            const canvasPosition = canvas.getBoundingClientRect();
//                            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
//                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
//
//                            if (canvasPosition && tooltipEl) {
//                                tooltipEl.style.left = (canvasPosition.left + scrollLeft + event.x) + 'px';
//                                tooltipEl.style.top = (canvasPosition.top + scrollTop + event.y - 10) + 'px';
//                            }
//                        } catch (error) {
//                            console.warn('Error positioning donut tooltip:', error);
//                            if (tooltipEl) {
//                                tooltipEl.style.opacity = 0;
//                            }
//                        }
//                    },
//                    cutout: '50%',  // Donut hole size
//                }
//            });
//
//            this.charts.set(containerId, chart);
//            return chart;
//
//        } catch (error) {
//            console.error('Error creating donut chart:', error);
//            return null;
//        }
//    }
}

// Global instance
window.chartManager = new ChartManager();

// HTMX integration - only destroy charts when the swap actually affects them
document.addEventListener('htmx:beforeSwap', function(event) {
    if (!window.chartManager) return;
    
    // Get the target element that will be swapped
    const swapTarget = event.detail.target || event.target;
    if (!swapTarget) return;
    
    // Special case: Never destroy charts when targeting body element
    // Charts are in specific containers, and operations on body (like modal appends) shouldn't affect them
    if (swapTarget === document.body || swapTarget.tagName === 'BODY') {
        return;
    }

    const chartsToDestroy = [];
    window.chartManager.charts.forEach((chart, containerId) => {
        const chartCanvas = document.getElementById(containerId);
        if (chartCanvas && swapTarget.contains(chartCanvas)) {
            chartsToDestroy.push(containerId);
        }
    });
    
    // Only destroy charts that will actually be affected by the swap
    if (chartsToDestroy.length > 0) {
        chartsToDestroy.forEach(containerId => {
            window.chartManager.destroyChart(containerId);
        });
    }
});