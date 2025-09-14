from fasthtml import ft
from typing import Any, List, Dict
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
import json
import time

def create_line_chart(container_id: str, data: List[dict[str, Any]], 
                     y_key: str = "winRate", x_key: str = "meta", 
                     y_label: str = "Win Rate", y_suffix: str = "%",
                     color: ChartColors = ChartColors.NEUTRAL,
                     show_x_axis: bool = True,
                     show_y_axis: bool = True) -> ft.Div:
    """
    Creates a line chart using Chart.js
    
    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries containing the data points
        y_key: Key for the y-axis values in the data dictionaries
        x_key: Key for the x-axis values in the data dictionaries
        y_label: Label for the y-axis values in tooltips
        y_suffix: Suffix to add to y-axis values (e.g., "%")
        color: Color theme for the chart from ChartColors enum
        show_x_axis: Whether to show the x-axis
        show_y_axis: Whether to show the y-axis
    """
    # Convert Python data to JSON string
    json_data = json.dumps(data)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"  # Use full height and width
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const container = document.getElementById(chartId);
                
                if (!container) {{
                    console.error('Chart container not found:', chartId);
                }} else {{
                    // Destroy existing chart if it exists
                    const existingChart = Chart.getChart(chartId);
                    if (existingChart) {{
                        existingChart.destroy();
                    }}
                    
                    const data = {json_data};
                    
                    new Chart(container, {{
                        type: 'line',
                        data: {{
                            labels: data.map(d => d['{x_key}']),
                            datasets: [{{
                                data: data.map(d => d['{y_key}']),
                                borderColor: '{color}',
                                backgroundColor: '{color}',
                                tension: 0.3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                borderWidth: 2,
                                spanGaps: true,
                                segment: {{
                                    borderDash: ctx => !ctx.p0.raw || !ctx.p1.raw ? [6, 6] : undefined
                                }},
                                pointStyle: 'circle',
                                pointBackgroundColor: data.map(d => d['{y_key}'] === null ? 'transparent' : '{color}'),
                                pointBorderColor: data.map(d => d['{y_key}'] === null ? '{color}' : '{color}')
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            animation: {{
                                duration: 300
                            }},
                            plugins: {{
                                legend: {{
                                    display: false
                                }},
                                tooltip: {{
                                    backgroundColor: '{ChartColors.TOOLTIP_BG}',
                                    titleColor: '#ffffff',
                                    bodyColor: '#ffffff',
                                    borderColor: '{ChartColors.TOOLTIP_BORDER}',
                                    borderWidth: 1,
                                    padding: 8,
                                    displayColors: false,
                                    callbacks: {{
                                        label: function(context) {{
                                            return context.raw === null ? 'No data' : context.parsed.y + '{y_suffix}';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    display: {str(show_x_axis).lower()},
                                    grid: {{
                                        display: false
                                    }},
                                    ticks: {{
                                        color: '{ChartColors.TICK_TEXT}',
                                        font: {{
                                            size: 10
                                        }},
                                        maxRotation: 45,
                                        minRotation: 45,
                                        padding: 5
                                    }}
                                }},
                                y: {{
                                    display: {str(show_y_axis).lower()},
                                    grid: {{
                                        display: {str(show_y_axis).lower()}
                                    }},
                                    ticks: {{
                                        display: {str(show_y_axis).lower()},
                                        color: '{ChartColors.TICK_TEXT}',
                                        font: {{
                                            size: 10
                                        }},
                                        padding: 5,
                                        callback: function(value) {{
                                            return value + '{y_suffix}';
                                        }}
                                    }}
                                }}
                            }},
                            layout: {{
                                padding: {{
                                    top: 5,
                                    right: 5,
                                    bottom: 5,
                                    left: 5
                                }}
                            }}
                        }}
                    }});
                }}
            }})();
        """),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    ) 

def create_leader_win_rate_radar_chart(container_id, data, leader_ids, colors=None, show_legend=True):
    """
    Create a radar chart to display leader win rates against different color matchups.
    
    Args:
        container_id: HTML ID for the chart container
        data: Radar chart data with color matchups
        leader_ids: List of leader IDs to include in the chart
        colors: List of colors for each leader
        show_legend: Whether to show the chart legend
    """
    if not data or not leader_ids:
        return ft.Div(ft.P("No data available for radar chart.", cls="text-gray-400"))
    
    # Filter data for the specified leaders
    filtered_data = []
    for item in data:
        if item.get('leader_id') in leader_ids:
            filtered_data.append(item)
    
    # Default colors if none provided
    if not colors or len(colors) != len(leader_ids):
        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"][:len(leader_ids)]
    
    # Convert data to the format needed for the radar chart
    radar_data = []
    for item in filtered_data:
        leader_data = {"leader": item.get('leader_id', '')}
        
        # Add color win rate data
        for key, value in item.items():
            if key != 'leader_id' and not key.startswith('__'):
                leader_data[key] = value
        
        radar_data.append(leader_data)
    
    # Convert Python data to JSON safely
    import json
    json_radar_data = json.dumps(radar_data)
    json_leader_ids = json.dumps(leader_ids)
    json_colors = json.dumps(colors)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const container = document.getElementById(chartId);
                
                if (!container) {{
                    console.error('Chart container not found:', chartId);
                    return;
                }}
                
                // Destroy existing chart if it exists
                const existingChart = Chart.getChart(chartId);
                if (existingChart) {{
                    existingChart.destroy();
                }}
                
                // Prepare data
                const data = {json_radar_data};
                const leaders = {json_leader_ids};
                const colors = {json_colors};
                
                if (data.length === 0 || !data[0]) {{
                    console.error('No valid data for chart');
                    return;
                }}
                
                // Extract labels from first data object
                const labels = Object.keys(data[0]).filter(key => key !== 'leader');
                
                // Prepare datasets
                const datasets = data.map((item, index) => {{
                    return {{
                        label: item.leader,
                        data: labels.map(label => item[label]),
                        backgroundColor: colors[index] + '33', // Add transparency
                        borderColor: colors[index],
                        pointBackgroundColor: colors[index],
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: colors[index]
                    }};
                }});
                
                // Create chart
                new Chart(container, {{
                    type: 'radar',
                    data: {{
                        labels: labels,
                        datasets: datasets
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: {str(show_legend).lower()},
                                position: 'bottom',
                                labels: {{
                                    color: '#ffffff',
                                    font: {{
                                        size: 16 // Increased font size
                                    }}
                                }}
                            }},
                        }},
                        scales: {{
                            r: {{
                                angleLines: {{
                                    color: 'rgba(255, 255, 255, 0.2)'
                                }},
                                grid: {{
                                    color: 'rgba(255, 255, 255, 0.2)'
                                }},
                                pointLabels: {{
                                    color: '#ffffff',
                                    font: {{
                                        size: 16 // Increased font size
                                    }}
                                }},
                                ticks: {{
                                    color: '#ffffff',
                                    backdropColor: 'transparent'
                                }}
                            }}
                        }},
                    }}
                }});
            }})();
        """),
        cls="radar-chart-container bg-gray-800 rounded-lg p-4 shadow-lg",
        style="height: 300px; width: 100%;"  # Explicit height and width
    ) 

def create_bar_chart(container_id: str, data: List[dict[str, Any]], 
                    y_key: str = "matches", x_key: str = "meta",
                    y_label: str = "Matches", y_suffix: str = " matches",
                    color: ChartColors = ChartColors.NEUTRAL,
                    show_x_axis: bool = True,
                    show_y_axis: bool = True) -> ft.Div:
    """
    Creates a bar chart using Chart.js
    
    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries containing the data points
        y_key: Key for the y-axis values in the data dictionaries
        x_key: Key for the x-axis values in the data dictionaries
        y_label: Label for the y-axis values in tooltips
        y_suffix: Suffix to add to y-axis values (e.g., " matches")
        color: Color theme for the chart from ChartColors enum
        show_x_axis: Whether to show the x-axis
        show_y_axis: Whether to show the y-axis
    """
    # Convert Python data to JSON string
    json_data = json.dumps(data)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const container = document.getElementById(chartId);
                
                if (!container) {{
                    console.error('Chart container not found:', chartId);
                    return;
                }}
                
                // Destroy existing chart if it exists
                const existingChart = Chart.getChart(chartId);
                if (existingChart) {{
                    existingChart.destroy();
                }}
                
                const data = {json_data};
                
                new Chart(container, {{
                    type: 'bar',
                    data: {{
                        labels: data.map(d => d['{x_key}']),
                        datasets: [{{
                            data: data.map(d => d['{y_key}']),
                            backgroundColor: '{color}',
                            borderColor: '{color}',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                backgroundColor: '{ChartColors.TOOLTIP_BG}',
                                titleColor: '#ffffff',
                                bodyColor: '#ffffff',
                                borderColor: '{ChartColors.TOOLTIP_BORDER}',
                                borderWidth: 1,
                                padding: 8,
                                displayColors: false,
                                callbacks: {{
                                    label: function(context) {{
                                        return context.raw + '{y_suffix}';
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{
                                display: {str(show_x_axis).lower()},
                                grid: {{
                                    display: false
                                }},
                                ticks: {{
                                    color: '{ChartColors.TICK_TEXT}',
                                    font: {{
                                        size: 10
                                    }},
                                    maxRotation: 45,
                                    minRotation: 45,
                                    padding: 5
                                }}
                            }},
                            y: {{
                                display: {str(show_y_axis).lower()},
                                grid: {{
                                    display: {str(show_y_axis).lower()}
                                }},
                                ticks: {{
                                    color: '{ChartColors.TICK_TEXT}',
                                    font: {{
                                        size: 10
                                    }},
                                    padding: 5,
                                    stepSize: 1
                                }}
                            }}
                        }}
                    }}
                }});
            }})();
        """),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    ) 

def create_stream_chart(container_id: str, data: List[dict[str, Any]], 
                       y_key: str = "wins", x_key: str = "date",
                       y_label: str = "Tournament Wins", y_suffix: str = " wins",
                       color: str = ChartColors.POSITIVE,
                       show_x_axis: bool = True,
                       show_y_axis: bool = True) -> ft.Div:
    """
    Creates a stream chart using Chart.js with gradient fill and smooth transitions.
    Also includes a bar chart overlay for individual data points.
    
    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries containing the data points
        y_key: Key for the y-axis values in the data dictionaries
        x_key: Key for the x-axis values in the data dictionaries (should be date strings)
        y_label: Label for the y-axis values in tooltips
        y_suffix: Suffix to add to y-axis values (e.g., " wins")
        color: Color for the chart line and gradient
        show_x_axis: Whether to show the x-axis
        show_y_axis: Whether to show the y-axis
    """
    # Convert Python data to JSON string
    json_data = json.dumps(data)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const container = document.getElementById(chartId);
                
                if (!container) {{
                    console.error('Chart container not found:', chartId);
                    return;
                }}
                
                // Destroy existing chart if it exists
                const existingChart = Chart.getChart(chartId);
                if (existingChart) {{
                    existingChart.destroy();
                }}
                
                const data = {json_data};
                
                // Get the chart context and create gradient
                const ctx = container.getContext('2d');
                const gradient = ctx.createLinearGradient(0, 0, 0, container.height);
                gradient.addColorStop(0, '{color}');  // Start with full color
                gradient.addColorStop(1, '{color}00'); // End with transparent
                
                // Create cumulative data for stream effect
                let cumulativeData = [];
                let runningTotal = 0;
                data.forEach(d => {{
                    runningTotal += d['{y_key}'];
                    cumulativeData.push(runningTotal);
                }});
                
                // Format dates for display - shorter format
                const formatDate = (dateStr) => {{
                    const date = new Date(dateStr);
                    const month = date.toLocaleDateString('en-US', {{ month: 'short' }});
                    const year = date.getFullYear().toString().slice(2); // Get last 2 digits of year
                    return `${{month}} '${{year}}`;
                }};
                
                // Group data points by month to avoid duplicate labels
                const monthLabels = new Map();
                data.forEach((d, i) => {{
                    const date = new Date(d['{x_key}']);
                    const monthKey = `${{date.getFullYear()}}-${{date.getMonth()}}`;
                    if (!monthLabels.has(monthKey)) {{
                        monthLabels.set(monthKey, i);
                    }}
                }});
                
                // Define consistent colors for dark mode
                const COLORS = {{
                    BAR: '#9CA3AF',  // A medium gray that's visible but not too bright
                    BAR_BORDER: '#D1D5DB',  // Slightly lighter gray for bar borders
                    AXIS_TEXT: '#E5E7EB',  // Light gray for axis text
                    GRID: 'rgba(255, 255, 255, 0.1)'  // Subtle grid lines
                }};
                
                // Find max values for scaling
                const maxWins = Math.max(...data.map(d => d['{y_key}']));
                const maxCumulative = Math.max(...cumulativeData);
                
                new Chart(container, {{
                    data: {{
                        labels: data.map(d => formatDate(d['{x_key}'])),
                        datasets: [
                            // Bar chart for individual wins
                            {{
                                type: 'bar',
                                data: data.map(d => d['{y_key}']),
                                backgroundColor: COLORS.BAR,
                                borderColor: COLORS.BAR_BORDER,
                                borderWidth: 1,
                                barPercentage: 0.4,
                                order: 2,
                                yAxisID: 'y-axis-bars',
                                barThickness: 'flex',
                                minBarLength: 10
                            }},
                            // Line chart for cumulative wins
                            {{
                                type: 'line',
                                data: cumulativeData,
                                borderColor: '{color}',
                                backgroundColor: gradient,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                borderWidth: 2,
                                pointStyle: 'circle',
                                pointBackgroundColor: '{color}',
                                pointBorderColor: '#fff',
                                order: 1,
                                yAxisID: 'y-axis-line'
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {{
                            duration: 1000,
                            easing: 'easeInOutQuart'
                        }},
                        interaction: {{
                            mode: 'nearest',
                            axis: 'x',
                            intersect: false
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                backgroundColor: '{ChartColors.TOOLTIP_BG}',
                                titleColor: '#ffffff',
                                bodyColor: '#ffffff',
                                borderColor: '{ChartColors.TOOLTIP_BORDER}',
                                borderWidth: 1,
                                padding: 8,
                                displayColors: false,
                                callbacks: {{
                                    title: function(context) {{
                                        return data[context[0].dataIndex]['{x_key}'];
                                    }},
                                    label: function(context) {{
                                        if (context.datasetIndex === 0) {{
                                            return 'Wins on this day: ' + context.parsed.y + '{y_suffix}';
                                        }} else {{
                                            return 'Total wins: ' + context.parsed.y + '{y_suffix}';
                                        }}
                                    }}
                                }}
                            }},
                        }},
                        scales: {{
                            x: {{
                                display: {str(show_x_axis).lower()},
                                grid: {{
                                    display: false
                                }},
                                ticks: {{
                                    color: COLORS.AXIS_TEXT,
                                    font: {{
                                        size: 10
                                    }},
                                    maxRotation: 0,
                                    minRotation: 0,
                                    padding: 8,
                                    autoSkip: false,
                                    callback: function(value, index) {{
                                        const date = new Date(data[index]['{x_key}']);
                                        const monthKey = `${{date.getFullYear()}}-${{date.getMonth()}}`;
                                        return monthLabels.get(monthKey) === index ? this.getLabelForValue(value) : '';
                                    }}
                                }}
                            }},
                            'y-axis-bars': {{
                                display: {str(show_y_axis).lower()},
                                position: 'left',
                                grid: {{
                                    display: false
                                }},
                                ticks: {{
                                    color: COLORS.AXIS_TEXT,
                                    font: {{
                                        size: 10
                                    }},
                                    padding: 5,
                                    callback: function(value) {{
                                        return value + '{y_suffix}';
                                    }},
                                    stepSize: 1
                                }},
                                min: 0,
                                max: Math.max(maxWins * 1.2, 4),
                                border: {{
                                    color: COLORS.BAR_BORDER
                                }}
                            }},
                            'y-axis-line': {{
                                display: {str(show_y_axis).lower()},
                                position: 'right',
                                grid: {{
                                    display: {str(show_y_axis).lower()},
                                    color: COLORS.GRID
                                }},
                                ticks: {{
                                    color: COLORS.AXIS_TEXT,
                                    font: {{
                                        size: 10
                                    }},
                                    padding: 5,
                                    callback: function(value) {{
                                        return value + '{y_suffix}';
                                    }}
                                }},
                                min: 0,
                                max: Math.ceil(maxCumulative * 1.1),
                                border: {{
                                    color: COLORS.BAR_BORDER
                                }}
                            }}
                        }},
                        layout: {{
                            padding: {{
                                top: 20,
                                right: 30,
                                bottom: 20,
                                left: 30
                            }}
                        }}
                    }}
                }});
            }})();
        """),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    ) 

def create_bubble_chart(container_id: str, data: List[Dict[str, Any]], colors: List[str], title: str = "Leader Tournament Popularity"):
    """
    Create a bubble chart for leader tournament statistics.
    
    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries containing the data points
        colors: List of color strings for each bubble
        title: Chart title
    """
    # Convert data to JSON strings
    data_json = json.dumps(data)
    colors_json = json.dumps(colors)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"  # Use full height and width
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const chartData = {data_json};
                const chartColors = {colors_json};
                const chartTitle = '{title}';
                
                // Store data globally for recreation
                window.bubbleChartData = {{
                    data: chartData,
                    colors: chartColors,
                    title: chartTitle,
                    containerId: chartId
                }};
                
                function createBubbleChart() {{
                    // Clean up old tooltip if it exists
                    const oldTooltip = document.getElementById('chartjs-tooltip');
                    if (oldTooltip) {{
                        oldTooltip.remove();
                    }}
                    
                    // Clean up old chart event listeners using a stable reference
                    if (window.bubbleChartHideTooltipHandler) {{
                        try {{ document.removeEventListener('mouseout', window.bubbleChartHideTooltipHandler); }} catch (e) {{}}
                    }}
                    
                    function hideTooltip() {{
                        const tooltipEl = document.getElementById('chartjs-tooltip');
                        if (tooltipEl) {{
                            tooltipEl.style.opacity = 0;
                        }}
                    }}
                    
                    // Add global mouse out listener to hide tooltip when mouse leaves chart area
                    window.bubbleChartHideTooltipHandler = hideTooltip;
                    document.addEventListener('mouseout', window.bubbleChartHideTooltipHandler);
                    
                    const container = document.getElementById(chartId);
                    if (!container) {{
                        console.error('Chart container not found:', chartId);
                        return null;
                    }}
                    
                    // Destroy existing chart if it exists
                    const existingChart = Chart.getChart(chartId);
                    if (existingChart) {{
                        existingChart.destroy();
                    }}
                    
                    // Clear the canvas and reset its size
                    const ctx = container.getContext('2d');
                    ctx.clearRect(0, 0, container.width, container.height);
                    
                    // Reset canvas size to match container
                    const containerElement = container.parentElement;
                    if (containerElement) {{
                        container.width = containerElement.clientWidth;
                        container.height = containerElement.clientHeight;
                    }}
                    
                    // Store multi-color data for custom drawing
                    const multiColorData = chartColors.map((colorData, index) => {{
                        if (Array.isArray(colorData) && colorData.length > 1) {{
                            return {{
                                isMultiColor: true,
                                colors: colorData,
                                dataIndex: index
                            }};
                        }}
                        return {{
                            isMultiColor: false,
                            colors: [Array.isArray(colorData) ? colorData[0] : colorData],
                            dataIndex: index
                        }};
                    }});
                    
                    // Process colors for Chart.js (use first color for multi-color leaders)
                    const processedColors = chartColors.map((colorData, index) => {{
                        if (Array.isArray(colorData) && colorData.length > 1) {{
                            // Multi-color leader - use first color as base (will be overdrawn by plugin)
                            const color = colorData[0];
                        const r = parseInt(color.slice(1,3), 16);
                        const g = parseInt(color.slice(3,5), 16);
                        const b = parseInt(color.slice(5,7), 16);
                        return `rgba(${{r}},${{g}},${{b}},0.7)`;
                        }} else {{
                            // Single color leader - add transparency
                            const color = Array.isArray(colorData) ? colorData[0] : colorData;
                        const r = parseInt(color.slice(1,3), 16);
                        const g = parseInt(color.slice(3,5), 16);
                        const b = parseInt(color.slice(5,7), 16);
                        return `rgba(${{r}},${{g}},${{b}},0.7)`;
                        }}
                    }});
                    
                    // Process hover colors for multi-color support (slightly more opaque)
                    const processedHoverColors = chartColors.map((colorData, index) => {{
                        if (Array.isArray(colorData) && colorData.length > 1) {{
                            // Multi-color leader - use first color but more opaque
                            const color = colorData[0];
                            const r = parseInt(color.slice(1,3), 16);
                            const g = parseInt(color.slice(3,5), 16);
                            const b = parseInt(color.slice(5,7), 16);
                            return `rgba(${{r}},${{g}},${{b}},0.9)`;
                        }} else {{
                            // Single color leader - more opaque on hover
                            const color = Array.isArray(colorData) ? colorData[0] : colorData;
                            const r = parseInt(color.slice(1,3), 16);
                            const g = parseInt(color.slice(3,5), 16);
                            const b = parseInt(color.slice(5,7), 16);
                            return `rgba(${{r}},${{g}},${{b}},0.9)`; // More opaque on hover
                        }}
                    }});
                    
                    // Process border colors (use first color for multi-color leaders)
                    const borderColors = chartColors.map(colorData => {{
                        return Array.isArray(colorData) ? colorData[0] : colorData;
                    }});
                    
                    // Custom plugin to draw multi-color segments
                    const multiColorPlugin = {{
                        id: 'multiColorBubbles',
                        afterDatasetsDraw: function(chart) {{
                            const ctx = chart.ctx;
                            const meta = chart.getDatasetMeta(0);
                            
                            meta.data.forEach((element, index) => {{
                                const colorInfo = multiColorData[index];
                                if (colorInfo && colorInfo.isMultiColor && colorInfo.colors.length > 1) {{
                                    const model = element;
                                    const x = model.x;
                                    const y = model.y;
                                    const radius = model.options.radius;
                                    
                                    // Draw pie-like segments within the bubble
                                    const colors = colorInfo.colors;
                                    const angleStep = (2 * Math.PI) / colors.length;
                                    
                                    ctx.save();
                                    
                                    colors.forEach((color, colorIndex) => {{
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
                                        ctx.fillStyle = `rgba(${{r}}, ${{g}}, ${{b}}, 0.7)`;
                                        ctx.fill();
                                        
                                        // Add subtle border
                                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
                                        ctx.lineWidth = 0.5;
                                        ctx.stroke();
                                    }});
                                    
                                    ctx.restore();
                                }}
                            }});
                        }}
                    }};
                    
                    const chart = new Chart(container, {{
                        type: 'bubble',
                        data: {{
                            datasets: [{{
                                data: chartData,
                                backgroundColor: processedColors,
                                borderColor: borderColors,
                                borderWidth: 1,
                                hoverBackgroundColor: processedHoverColors, // Enhanced hover colors
                                radius: (context) => {{
                                    // Get the bubble size from the data
                                    return context.raw.r;
                                }}
                            }}]
                        }},
                        plugins: [multiColorPlugin],
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            layout: {{
                                padding: {{
                                    top: 20,
                                    right: 20,
                                    bottom: 50,  // Increased bottom padding to show x-axis properly
                                    left: window.innerWidth > 768 ? 50 : 30
                                }}
                            }},
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: chartTitle,
                                    color: 'white',
                                    font: {{ size: 16 }},
                                    padding: {{ bottom: 10 }}
                                }},
                                legend: {{
                                    display: false
                                }},
                                tooltip: {{
                                    enabled: false,  // Disable default tooltip
                                }},
                            }},
                            hover: {{
                                mode: 'nearest',
                                intersect: true
                            }},
                            events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
                            onHover: function(event, chartElements) {{
                                let tooltipEl = document.getElementById('chartjs-tooltip');
                                
                                if (!tooltipEl) {{
                                    const div = document.createElement('div');
                                    div.id = 'chartjs-tooltip';
                                    div.style.position = 'absolute';
                                    div.style.pointerEvents = 'none';
                                    div.style.opacity = '0';
                                    div.style.transition = 'all .1s ease';
                                    document.body.appendChild(div);
                                    tooltipEl = div;
                                }}
                                
                                if (!chartElements || chartElements.length === 0) {{
                                    if (tooltipEl) {{
                                    tooltipEl.style.opacity = 0;
                                    }}
                                    return;
                                }}
                                
                                const element = chartElements[0];
                                const data = element.element.$context.raw;
                                const dataIndex = element.index;
                                const leaderColors = chartColors[dataIndex];
                                
                                // Create color indicators for multi-color leaders
                                const colorIndicators = Array.isArray(leaderColors) && leaderColors.length > 1 
                                    ? leaderColors.map(color => `<span style="display: inline-block; width: 12px; height: 12px; background-color: ${{color}}; margin-right: 4px; border-radius: 2px;"></span>`).join('')
                                    : '';
                                
                                // Create tooltip content with responsive layout
                                const isMobile = window.innerWidth <= 768;
                                const tooltipContent = `
                                    <div style="
                                        display: flex;
                                        gap: ${{isMobile ? '8px' : '16px'}};
                                        min-width: ${{isMobile ? '280px' : '400px'}};
                                        height: ${{isMobile ? '120px' : '150px'}};
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
                                            ${{data.image ? `<img src="${{data.image}}" style="width: 100%; height: 100%; object-fit: contain; display: block;">` : ''}}
                                        </div>
                                        <div style="
                                            flex: 0 0 70%;
                                            padding: ${{isMobile ? '8px 12px 8px 0' : '12px 16px 12px 0'}};
                                            display: flex;
                                            flex-direction: column;
                                            justify-content: center;
                                        ">
                                            <div style="font-weight: bold; margin-bottom: ${{isMobile ? '8px' : '12px'}}; font-size: ${{isMobile ? '1em' : '1.2em'}}; white-space: normal;">${{data.name}}</div>
                                            <div style="margin: ${{isMobile ? '2px' : '4px'}} 0; font-size: ${{isMobile ? '0.9em' : '1em'}};">Win Rate: ${{(data.y * 100).toFixed(1)}}%</div>
                                            <div style="margin: ${{isMobile ? '2px' : '4px'}} 0; font-size: ${{isMobile ? '0.9em' : '1em'}};">Tournament Matches: ${{data.x}}</div>
                                            <div style="margin: ${{isMobile ? '2px' : '4px'}} 0; font-size: ${{isMobile ? '0.9em' : '1em'}};">Tournament Wins: ${{data.raw_wins}}</div>
                                            ${{colorIndicators ? `<div style="margin: ${{isMobile ? '6px' : '8px'}} 0 ${{isMobile ? '2px' : '4px'}} 0; font-size: ${{isMobile ? '0.85em' : '0.9em'}};"><strong>Colors:</strong></div><div style="margin: ${{isMobile ? '2px' : '4px'}} 0;">${{colorIndicators}}</div>` : ''}}
                                        </div>
                                    </div>
                                `;
                                
                                tooltipEl.innerHTML = tooltipContent;
                                tooltipEl.style.opacity = 1;
                                tooltipEl.style.position = 'absolute';
                                tooltipEl.style.backgroundColor = '{ChartColors.TOOLTIP_BG}';
                                tooltipEl.style.color = '#ffffff';
                                tooltipEl.style.borderRadius = '4px';
                                tooltipEl.style.border = '1px solid {ChartColors.TOOLTIP_BORDER}';
                                tooltipEl.style.pointerEvents = 'none';
                                tooltipEl.style.zIndex = 9999;
                                tooltipEl.style.transform = 'translate(-50%, -100%)';
                                tooltipEl.style.transition = 'all .1s ease';
                                tooltipEl.style.padding = '0';
                                tooltipEl.style.overflow = 'hidden';
                                
                                // Position the tooltip safely
                                try {{
                                    const chartRect = container.getBoundingClientRect();
                                    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                    
                                    // Try multiple methods to get element position
                                    let x, y;
                                    if (element.element && element.element.tooltipPosition) {{
                                        const position = element.element.tooltipPosition();
                                        x = position.x;
                                        y = position.y;
                                    }} else if (element.element && element.element.x !== undefined) {{
                                        x = element.element.x;
                                        y = element.element.y;
                                    }} else {{
                                        // Fallback to chart center
                                        x = chartRect.width / 2;
                                        y = chartRect.height / 2;
                                    }}
                                    
                                    if (x !== undefined && y !== undefined && tooltipEl) {{
                                        tooltipEl.style.left = (chartRect.left + scrollLeft + x) + 'px';
                                        tooltipEl.style.top = (chartRect.top + scrollTop + y - 10) + 'px';
                                    }}
                                }} catch (error) {{
                                    console.warn('Error positioning tooltip:', error);
                                    if (tooltipEl) {{
                                        tooltipEl.style.opacity = 0;
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    type: 'logarithmic',
                                    display: true,  // Always show x-axis
                                    title: {{
                                        display: window.innerWidth > 768,  // Hide title on mobile, but show axis
                                        text: 'Number of Tournament Matches',
                                        color: 'white',
                                        font: {{
                                            size: window.innerWidth > 768 ? 12 : 10
                                        }}
                                    }},
                                    ticks: {{
                                        display: true,  // Always show ticks
                                        color: '{ChartColors.TICK_TEXT}',
                                        font: {{
                                            size: window.innerWidth > 768 ? 10 : 8
                                        }},
                                        padding: window.innerWidth > 768 ? 5 : 2,
                                        maxTicksLimit: window.innerWidth > 768 ? 8 : 5,  // Fewer ticks on mobile
                                        maxRotation: 0,  // Prevent label rotation on mobile
                                        minRotation: 0
                                    }},
                                    grid: {{
                                        display: true,  // Always show grid
                                        color: 'rgba(255, 255, 255, 0.1)'
                                    }}
                                }},
                                y: {{
                                    display: true,  // Always show y-axis
                                    title: {{
                                        display: window.innerWidth > 768,  // Hide title on mobile, but show axis
                                        text: 'Win Rate',
                                        color: 'white',
                                        font: {{
                                            size: window.innerWidth > 768 ? 12 : 10
                                        }}
                                    }},
                                    ticks: {{
                                        display: true,  // Always show ticks
                                        color: '{ChartColors.TICK_TEXT}',
                                        font: {{
                                            size: window.innerWidth > 768 ? 10 : 8
                                        }},
                                        padding: window.innerWidth > 768 ? 5 : 2,
                                        maxTicksLimit: window.innerWidth > 768 ? 8 : 5,  // Fewer ticks on mobile
                                        callback: function(value) {{
                                            return (value * 100).toFixed(0) + '%';
                                        }}
                                    }},
                                    grid: {{
                                        display: true,  // Always show grid
                                        color: 'rgba(255, 255, 255, 0.1)'
                                    }}
                                }}
                            }}
                        }}
                    }});
                    
                    // Store chart reference for cleanup
                    window.currentBubbleChart = chart;
                    
                    return chart;
                }}
                
                // Global function to recreate chart with current data
                window.recreateBubbleChart = function() {{
                    if (window.bubbleChartData) {{
                        console.log('Recreating bubble chart with data:', window.bubbleChartData);
                        return createBubbleChart();
                    }} else {{
                        console.warn('No bubble chart data available for recreation');
                        return null;
                    }}
                }};
                
                // Create the initial chart
                createBubbleChart();
            }})();
        """),
        style="height: 300px; width: 100%;"  # Reduced height to leave room for slider
    ) 

def create_donut_chart(container_id: str, labels: List[str], values: List[int], colors: List, images: List[str], leader_ids: List[str] = None) -> ft.Div:
    """
    Create a donut chart for displaying data with multi-color support.
    
    Args:
        container_id: Unique ID for the chart container
        labels: List of labels for each segment
        values: List of values for each segment  
        colors: List of colors (can be arrays for multi-color leaders)
        images: List of image URLs for tooltips
        leader_ids: List of leader IDs corresponding to each segment (for click handling)
    """
    # Convert data to JSON strings
    labels_json = json.dumps(labels)
    values_json = json.dumps(values)
    colors_json = json.dumps(colors)
    images_json = json.dumps(images)
    leader_ids_json = json.dumps(leader_ids or labels)
    
    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"
        ),
        ft.Script(f"""
            (function() {{
                const chartId = '{container_id}';
                const labels = {labels_json};
                const values = {values_json};
                const colors = {colors_json};
                const images = {images_json};
                const leaderIds = {leader_ids_json};
                
                function createDonutChart() {{
                    const canvas = document.getElementById(chartId);
                    if (!canvas || !window.Chart) return;
                    
                    // Destroy existing chart more thoroughly
                    const existing = window.Chart.getChart ? window.Chart.getChart(chartId) : null;
                    if (existing) {{
                        existing.destroy();
                    }}
                    
                    // Clear canvas completely
                    const ctx = canvas.getContext('2d');
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    
                    // Reset canvas size to container
                    const container = canvas.parentElement;
                    if (container) {{
                        canvas.width = container.clientWidth;
                        canvas.height = container.clientHeight;
                    }}
                    
                    const total = (Array.isArray(values) ? values : []).reduce((a,b)=>a+(+b||0),0) || 1;
                    
                    // Store multi-color data for custom drawing
                    const multiColorData = colors.map((colorData, index) => {{
                        if (Array.isArray(colorData) && colorData.length > 1) {{
                            return {{
                                isMultiColor: true,
                                colors: colorData,
                                dataIndex: index
                            }};
                        }}
                        return {{
                            isMultiColor: false,
                            colors: [Array.isArray(colorData) ? colorData[0] : colorData],
                            dataIndex: index
                        }};
                    }});
                    
                    // Process colors for Chart.js (make multi-color leaders transparent; plugin will paint them)
                    const processedColors = colors.map((colorData, index) => {{
                        if (Array.isArray(colorData) && colorData.length > 1) {{
                            // Multi-color leader - transparent base so plugin colors are the only visible fill
                            return 'rgba(0,0,0,0)';
                        }} else {{
                            // Single color leader
                            return Array.isArray(colorData) ? colorData[0] : colorData;
                        }}
                    }});
                    
                    const data = {{
                        labels: labels,
                        datasets: [{{
                            data: values,
                            backgroundColor: function(ctx) {{
                                try {{
                                    const idx = ctx.dataIndex;
                                    const colorData = colors[idx];
                                    // Single color: return the color directly
                                    if (!Array.isArray(colorData) || colorData.length <= 1) {{
                                        return Array.isArray(colorData) ? colorData[0] : colorData;
                                    }}
                                    // Multi color: build conic gradient aligned to the arc
                                    const el = ctx.chart.getDatasetMeta(0).data[idx];
                                    if (!el) return 'rgba(0,0,0,0)';
                                    
                                    // Get arc properties - try multiple methods to ensure we get valid values
                                    let x, y, startAngle, endAngle;
                                    
                                    if (el.getProps) {{
                                        // Try animated properties first
                                        const props = el.getProps(['x','y','startAngle','endAngle'], true);
                                        if (props && props.x != null) {{
                                            x = props.x;
                                            y = props.y;
                                            startAngle = props.startAngle;
                                            endAngle = props.endAngle;
                                        }}
                                    }}
                                    
                                    // Fallback to static properties if needed
                                    if (x == null) {{
                                        x = el.x;
                                        y = el.y;
                                        startAngle = el.startAngle;
                                        endAngle = el.endAngle;
                                    }}
                                    
                                    // Final fallback to chart center
                                    if (x == null) {{
                                        const chartArea = ctx.chart.chartArea;
                                        x = (chartArea.left + chartArea.right) / 2;
                                        y = (chartArea.top + chartArea.bottom) / 2;
                                        startAngle = 0;
                                        endAngle = Math.PI * 2;
                                    }}
                                    
                                    const totalAngle = Math.max(1e-6, endAngle - startAngle);
                                    const grad = ctx.chart.ctx.createConicGradient(startAngle, x, y);
                                    const step = totalAngle / colorData.length;
                                    
                                    for (let i=0; i<colorData.length; i++) {{
                                        const start = (i*step) / (Math.PI*2);
                                        const end = ((i+1)*step) / (Math.PI*2);
                                        const col = colorData[i];
                                        grad.addColorStop(start, col);
                                        grad.addColorStop(end, col);
                                    }}
                                    return grad;
                                }} catch (e) {{
                                    console.warn('Error creating gradient:', e);
                                    return 'rgba(0,0,0,0)';
                                }}
                            }},
                            borderColor: 'transparent', // Remove grey borders for cleaner look
                            borderWidth: 0, // No borders
                            hoverBackgroundColor: function(ctx) {{
                                try {{
                                    const idx = ctx.dataIndex;
                                    const colorData = colors[idx];
                                    // Single color: brighten a bit
                                    if (!Array.isArray(colorData) || colorData.length <= 1) {{
                                        const base = Array.isArray(colorData) ? colorData[0] : colorData;
                                        const r = parseInt(base.slice(1,3),16), g = parseInt(base.slice(3,5),16), b = parseInt(base.slice(5,7),16);
                                        const br = Math.min(255, Math.round(r*1.1)), bg = Math.min(255, Math.round(g*1.1)), bb = Math.min(255, Math.round(b*1.1));
                                        return `rgb(${{br}}, ${{bg}}, ${{bb}})`;
                                    }}
                                    // Multi color: brighten each stop
                                    const el = ctx.chart.getDatasetMeta(0).data[idx];
                                    if (!el || !el.getProps) return 'rgba(0,0,0,0)';
                                    const props = el.getProps(['x','y','startAngle','endAngle'], true);
                                    const totalAngle = Math.max(1e-6, props.endAngle - props.startAngle);
                                    const grad = ctx.chart.ctx.createConicGradient(props.startAngle, props.x, props.y);
                                    const step = totalAngle / colorData.length;
                                    for (let i=0; i<colorData.length; i++) {{
                                        const start = (i*step) / (Math.PI*2);
                                        const end = ((i+1)*step) / (Math.PI*2);
                                        const base = colorData[i];
                                        const r = parseInt(base.slice(1,3),16), g = parseInt(base.slice(3,5),16), b = parseInt(base.slice(5,7),16);
                                        const br = Math.min(255, Math.round(r*1.1)), bg = Math.min(255, Math.round(g*1.1)), bb = Math.min(255, Math.round(b*1.1));
                                        const col = `rgb(${{br}}, ${{bg}}, ${{bb}})`;
                                        grad.addColorStop(start, col);
                                        grad.addColorStop(end, col);
                                    }}
                                    return grad;
                                }} catch (e) {{
                                    return 'rgba(0,0,0,0)';
                                }}
                            }},
                            hoverBorderColor: 'transparent', // No border on hover
                            hoverBorderWidth: 0, // No border thickness
                            hoverOffset: 8, // Native bounce for all segments
                            spacing: 4, // Increased spacing between segments for natural separation
                            borderRadius: 8, // Rounded edges for modern look
                            borderSkipped: false // Ensure all edges are rounded
                        }}]
                    }};
                    
                    const options = {{
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: {{
                            padding: 30  // More padding for better visual breathing room
                        }},
                        elements: {{
                            arc: {{
                                borderWidth: 0, // Ensure no borders on arcs
                                borderRadius: 6, // Rounded corners for individual segments
                                spacing: 3 // Additional spacing between elements
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                enabled: false  // Disable default tooltip, use custom one
                            }}
                        }},
                        hover: {{
                            mode: 'nearest',
                            intersect: true,
                            animationDuration: 200 // Match Chart.js default for consistency
                        }},
                        animation: {{
                            duration: 300,
                            easing: 'easeOutQuart' // Smooth animation curve
                        }},
                        events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
                        onClick: function(event, chartElements) {{
                            if (chartElements && chartElements.length > 0) {{
                                const element = chartElements[0];
                                const dataIndex = element.index;
                                const leaderId = leaderIds[dataIndex]; // Use the actual leader ID
                                
                                // Get current filter values from the page
                                const metaFormat = document.querySelector('[name="meta_format"]')?.value || '';
                                const region = document.querySelector('[name="region"]')?.value || '';
                                const days = document.querySelector('[name="days"]')?.value || '14';
                                const placing = document.querySelector('[name="placing"]')?.value || 'all';
                                
                                // Build URL with all current filters
                                const params = new URLSearchParams();
                                params.set('lid', leaderId);
                                if (metaFormat) params.set('meta_format', metaFormat);
                                if (region) params.set('region', region);
                                params.set('days', days);
                                params.set('placing', placing);
                                
                                // Open decklist modal with tournament filters
                                htmx.ajax('GET', '/api/decklist-modal?' + params.toString(), {{
                                    target: 'body',
                                    swap: 'beforeend'
                                }});
                            }}
                        }},
                        onHover: function(event, chartElements) {{
                            let tooltipEl = document.getElementById('chartjs-tooltip');
                            
                            if (!tooltipEl) {{
                                const div = document.createElement('div');
                                div.id = 'chartjs-tooltip';
                                div.style.position = 'absolute';
                                div.style.pointerEvents = 'none';
                                div.style.opacity = '0';
                                div.style.transition = 'all .1s ease';
                                document.body.appendChild(div);
                                tooltipEl = div;
                            }}
                            
                            if (!chartElements || chartElements.length === 0) {{
                                if (tooltipEl) {{
                                    tooltipEl.style.opacity = 0;
                                }}
                                return;
                            }}
                            
                            const element = chartElements[0];
                            const dataIndex = element.index;
                            const label = labels[dataIndex];
                            const value = values[dataIndex];
                            const image = images && images[dataIndex] ? images[dataIndex] : '';
                            const pct = ((value/total)*100).toFixed(1);
                            const leaderColors = colors[dataIndex];
                            
                            // Create color indicators for multi-color leaders
                            const colorIndicators = Array.isArray(leaderColors) && leaderColors.length > 1 
                                ? leaderColors.map(color => `<span style="display: inline-block; width: 12px; height: 12px; background-color: ${{color}}; margin-right: 4px; border-radius: 2px;"></span>`).join('')
                                : '';
                            
                            // Create tooltip content with flex layout
                            const tooltipContent = `
                                <div style="
                                    display: flex;
                                    gap: 16px;
                                    min-width: 300px;
                                    height: 120px;
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
                                        ${{image ? `<img src="${{image}}" style="width: 100%; height: 100%; object-fit: contain; display: block;">` : ''}}
                                    </div>
                                    <div style="
                                        flex: 0 0 70%;
                                        padding: 12px 16px 12px 0;
                                        display: flex;
                                        flex-direction: column;
                                        justify-content: center;
                                    ">
                                        <div style="font-weight: bold; margin-bottom: 12px; font-size: 1.2em; white-space: normal;">${{label}}</div>
                                        <div style="margin: 4px 0;">Count: ${{value}}</div>
                                        <div style="margin: 4px 0;">Percentage: ${{pct}}%</div>
                                        ${{colorIndicators ? `<div style="margin: 8px 0 4px 0;"><strong>Colors:</strong></div><div style="margin: 4px 0;">${{colorIndicators}}</div>` : ''}}
                                    </div>
                                </div>
                            `;
                            
                            tooltipEl.innerHTML = tooltipContent;
                            tooltipEl.style.opacity = 1;
                            tooltipEl.style.backgroundColor = '{ChartColors.TOOLTIP_BG}';
                            tooltipEl.style.color = '#ffffff';
                            tooltipEl.style.borderRadius = '4px';
                            tooltipEl.style.border = '1px solid {ChartColors.TOOLTIP_BORDER}';
                            tooltipEl.style.zIndex = 9999;
                            tooltipEl.style.transform = 'translate(-50%, -100%)';
                            tooltipEl.style.padding = '0';
                            tooltipEl.style.overflow = 'hidden';
                            
                            // Position the tooltip
                            try {{
                                const canvasPosition = canvas.getBoundingClientRect();
                                const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                
                                if (canvasPosition && tooltipEl) {{
                                    tooltipEl.style.left = (canvasPosition.left + scrollLeft + event.x) + 'px';
                                    tooltipEl.style.top = (canvasPosition.top + scrollTop + event.y - 10) + 'px';
                                }}
                            }} catch (error) {{
                                console.warn('Error positioning donut tooltip:', error);
                                if (tooltipEl) {{
                                    tooltipEl.style.opacity = 0;
                                }}
                            }}
                        }},
                        cutout: '50%',  // Donut hole size
                        animation: {{
                            duration: 300,  // Faster animation for HTMX updates
                            easing: 'easeOutQuart'
                        }},
                        elements: {{
                            arc: {{
                                borderWidth: 3,
                                borderColor: 'rgba(0, 0, 0, 0.1)'
                            }}
                        }}
                    }};
                    
                    // Custom plugin to draw multi-color segments in donut chart
                    const multiColorDonutPlugin = {{
                        id: 'multiColorDonut',
                        afterDatasetsDraw: function(chart) {{
                            const ctx = chart.ctx;
                            const meta = chart.getDatasetMeta(0);
                            const active = chart.getActiveElements ? chart.getActiveElements() : [];

                            meta.data.forEach((element, index) => {{
                                const colorInfo = multiColorData[index];
                                if (colorInfo && colorInfo.isMultiColor && colorInfo.colors.length > 1) {{
                                    // Use animated properties for perfect sync with native bounce
                                    const props = element.getProps
                                        ? element.getProps(['x','y','innerRadius','outerRadius','startAngle','endAngle'], true)
                                        : element; // fallback
                                    const centerX = props.x;
                                    const centerY = props.y;
                                    const innerRadius = props.innerRadius;
                                    const outerRadius = props.outerRadius;
                                    const startAngle = props.startAngle;
                                    const endAngle = props.endAngle;

                                    // Determine hover state using active elements
                                    const isHovered = Array.isArray(active) && active.some(a => a && a.datasetIndex === 0 && a.index === index);
                                    
                                    // Calculate the total angle of this segment
                                    const totalAngle = endAngle - startAngle;
                                    const colors = colorInfo.colors;
                                    const angleStep = totalAngle / colors.length;

                                    // Clip to current arc and paint wedges inside so native bounce stays
                                    ctx.save();
                                    ctx.beginPath();
                                    ctx.arc(centerX, centerY, outerRadius, startAngle, endAngle);
                                    ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
                                    ctx.closePath();
                                    ctx.clip();

                                    colors.forEach((color, colorIndex) => {{
                                        ctx.beginPath();
                                        
                                        const segmentStartAngle = startAngle + (colorIndex * angleStep);
                                        const segmentEndAngle = startAngle + ((colorIndex + 1) * angleStep);
                                        // Draw sub-arc inside the clipped arc
                                        ctx.arc(centerX, centerY, outerRadius, segmentStartAngle, segmentEndAngle);
                                        ctx.arc(centerX, centerY, innerRadius, segmentEndAngle, segmentStartAngle, true);
                                        ctx.closePath();
                                        
                                        // Apply slight brightness increase on hover for better visual feedback
                                        let fillColor = color;
                                        if (isHovered) {{
                                            // Parse color and brighten it slightly
                                            const r = parseInt(color.slice(1,3), 16);
                                            const g = parseInt(color.slice(3,5), 16);
                                            const b = parseInt(color.slice(5,7), 16);
                                            const brightR = Math.min(255, Math.round(r * 1.1));
                                            const brightG = Math.min(255, Math.round(g * 1.1));
                                            const brightB = Math.min(255, Math.round(b * 1.1));
                                            fillColor = `rgb(${{brightR}}, ${{brightG}}, ${{brightB}})`;
                                        }}
                                        
                                        ctx.fillStyle = fillColor;
                                        ctx.fill();
                                        
                                        // Add rounded caps for polished look
                                        ctx.lineCap = 'round';
                                        ctx.lineJoin = 'round';
                                    }});
                                    
                                    ctx.restore();
                                }}
                            }});
                        }}
                    }};
                    
                    // Small delay to ensure DOM is ready
                    setTimeout(() => {{
                        // Create chart with immediate render
                        const chart = new Chart(ctx, {{ 
                            type: 'doughnut', 
                            data, 
                            options: {{
                                ...options,
                                animation: {{
                                    ...options.animation,
                                    duration: 0  // Disable initial animation to ensure immediate render
                                }}
                            }}
                        }});

                        // Force immediate draw of multi-color segments
                        requestAnimationFrame(() => {{
                            // Re-enable animations for subsequent updates
                            chart.options.animation = options.animation;
                            // Force a redraw to apply multi-color gradients
                            chart.update('none');
                        }});
                    }}, 50);
                }}
                
                // Create the chart
                createDonutChart();
                
                // Cleanup on HTMX swaps - only when this specific chart's container is being replaced
                document.addEventListener('htmx:beforeSwap', function(event) {{
                    try {{
                        if (!window.Chart) return;
                        const target = event.target || (event.detail && event.detail.target);
                        
                        // Only cleanup if the target is exactly this chart's container
                        if (target && target.id === 'tournament-decklist-donut') {{
                            const chart = window.Chart.getChart ? window.Chart.getChart('{container_id}') : null;
                            if (chart) chart.destroy();
                            const tooltip = document.getElementById('chartjs-tooltip');
                            if (tooltip) tooltip.remove();
                        }}
                    }} catch(e) {{ /* noop */ }}
                }});
            }})();
        """),
        style="height: 340px; width: 100%;"
    ) 

def create_card_occurrence_streaming_chart(container_id: str, data: List[dict[str, Any]], 
                                        meta_formats: List[str], card_name: str, normalized: bool = False) -> ft.Div:
    """
    Creates a streaming chart showing card occurrences across meta formats and leaders using Chart.js.
    
    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries, each containing leader names as keys and occurrence counts as values
        meta_formats: List of meta format strings for x-axis labels
        card_name: Name of the card being displayed
        normalized: If True, normalize data so each meta format sums to 1 and create stacked chart
    """
    if not data or not any(data):
        return ft.Div(
            ft.P("No occurrence data available for this card.", cls="text-gray-400 text-center py-8"),
            cls="w-full"
        )
    
    # Extract all unique leader names from the data (already filtered by API)
    all_leaders = set()
    for meta_data in data:
        all_leaders.update(meta_data.keys())
    
    if not all_leaders:
        return ft.Div(
            ft.P("No leader data available for this card.", cls="text-gray-400 text-center py-8"),
            cls="w-full"
        )
    
    # Convert to sorted list to maintain consistent ordering from API
    filtered_leaders = []
    if data:
        # Use the order from the first meta format data to preserve API ordering
        filtered_leaders = list(data[0].keys())
    
    # Ensure all meta formats have all leaders (fill missing with 0)
    normalized_data = []
    for meta_data in data:
        normalized_meta = {}
        for leader in filtered_leaders:
            normalized_meta[leader] = meta_data.get(leader, 0)
        normalized_data.append(normalized_meta)
    
    # Apply normalization if requested
    if normalized:
        for i, meta_data in enumerate(normalized_data):
            total = sum(meta_data.values())
            if total > 0:
                normalized_data[i] = {leader: value / total for leader, value in meta_data.items()}
            else:
                normalized_data[i] = {leader: 0 for leader in filtered_leaders}
    
    # Generate distinct colors for each leader
    color_palette = [
        "#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
        "#06B6D4", "#F97316", "#84CC16", "#EC4899", "#6366F1"
    ]
    
    # Create a unique container ID to avoid conflicts
    unique_container_id = f"{container_id}-{int(time.time() * 1000)}"
    
    # Convert Python data to JSON strings
    data_json = json.dumps(normalized_data)
    meta_formats_json = json.dumps(meta_formats)
    leaders_json = json.dumps(filtered_leaders)
    colors_json = json.dumps(color_palette[:len(filtered_leaders)])
    
    # Chart type and configuration based on normalization
    chart_type = "line"
    y_axis_config = {
        "display": True,
        "stacked": normalized,  # Enable stacking for normalized mode
        "grid": {
            "display": True,
            "color": "rgba(255, 255, 255, 0.1)"
        },
        "ticks": {
            "color": "#9CA3AF",
            "font": {
                "size": 11
            },
            "padding": 8,
            "stepSize": 0.1 if normalized else 1,
            "callback": "function(value) { return " + (
                "(value * 100).toFixed(1) + '%'" if normalized else 
                'value + (value === 1 ? " occurrence" : " occurrences")'
            ) + "; }"
        },
        "beginAtZero": True
    }
    
    if normalized:
        y_axis_config["max"] = 1
    
    return ft.Div(
        ft.H3(
            f"Leader Occurrence for {card_name} ({'Normalized' if normalized else 'Absolute'})",
            cls="text-lg font-semibold text-white mb-4 text-center"
        ),
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=unique_container_id),
            cls="h-full w-full"
        ),
        # Script to clean up previous charts before this one loads
        ft.Script(f"""
            // Clean up any existing card occurrence charts first
            (function() {{
                // Destroy all existing Chart.js instances for card occurrence charts
                if (window.Chart && window.Chart.instances) {{
                    Object.keys(window.Chart.instances).forEach(key => {{
                        const chart = window.Chart.instances[key];
                        if (chart && chart.canvas && chart.canvas.id && chart.canvas.id.includes('card-occurrence-chart')) {{
                            chart.destroy();
                        }}
                    }});
                }}
                
                // Alternative cleanup for newer Chart.js versions
                if (window.Chart && window.Chart.registry) {{
                    const chartInstances = window.Chart.getChart ? 
                        document.querySelectorAll('canvas[id*="card-occurrence-chart"]') : [];
                    chartInstances.forEach(canvas => {{
                        const chart = window.Chart.getChart(canvas);
                        if (chart) {{
                            chart.destroy();
                        }}
                    }});
                }}
                
                // Clean up global storage
                if (window.cardOccurrenceChartInstances) {{
                    Object.keys(window.cardOccurrenceChartInstances).forEach(key => {{
                        if (key.includes('card-occurrence-chart')) {{
                            delete window.cardOccurrenceChartInstances[key];
                        }}
                    }});
                }}
            }})();
        """),
        ft.Script(f"""
            (function() {{
                const chartId = '{unique_container_id}';
                const container = document.getElementById(chartId);
                
                if (!container) {{
                    console.error('Chart container not found:', chartId);
                    return;
                }}
                
                // Clean up any existing tooltips
                const oldTooltips = document.querySelectorAll('#chartjs-tooltip');
                oldTooltips.forEach(tooltip => tooltip.remove());
                
                // Destroy existing chart if it exists
                const existingChart = Chart.getChart(chartId);
                if (existingChart) {{
                    existingChart.destroy();
                }}
                
                // Clear the canvas completely
                const ctx = container.getContext('2d');
                ctx.clearRect(0, 0, container.width, container.height);
                
                const rawData = {data_json};
                const metaFormats = {meta_formats_json};
                const leaders = {leaders_json};
                const colors = {colors_json};
                const isNormalized = {str(normalized).lower()};
                
                // Store chart data globally for potential recreation
                window.cardOccurrenceChartData = window.cardOccurrenceChartData || {{}};
                window.cardOccurrenceChartData[chartId] = {{
                    rawData: rawData,
                    metaFormats: metaFormats,
                    leaders: leaders,
                    colors: colors,
                    isNormalized: isNormalized,
                    containerId: chartId
                }};
                
                function createChart() {{
                    // Create datasets for each leader
                    const datasets = leaders.map((leader, index) => {{
                        const leaderData = rawData.map(meta => meta[leader] || 0);
                        
                        return {{
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
                        }};
                    }});
                    
                    const chart = new Chart(container, {{
                        type: 'line',
                        data: {{
                            labels: metaFormats,
                            datasets: datasets
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            animation: {{
                                duration: 800,
                                easing: 'easeInOutQuart'
                            }},
                            interaction: {{
                                mode: 'index',
                                intersect: false
                            }},
                            scales: {{
                                x: {{
                                    display: true,
                                    grid: {{
                                        display: false
                                    }},
                                    ticks: {{
                                        color: '#9CA3AF',
                                        font: {{
                                            size: 11
                                        }},
                                        maxRotation: 45,
                                        minRotation: 0,
                                        padding: 8
                                    }}
                                }},
                                y: {json.dumps(y_axis_config)}
                            }},
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'bottom',
                                    labels: {{
                                        color: '#E5E7EB',
                                        font: {{
                                            size: 10
                                        }},
                                        usePointStyle: true,
                                        pointStyle: 'circle',
                                        padding: 15,
                                        boxWidth: 8,
                                        boxHeight: 8
                                    }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                    titleColor: '#ffffff',
                                    bodyColor: '#ffffff',
                                    borderColor: '#374151',
                                    borderWidth: 1,
                                    padding: 12,
                                    displayColors: true,
                                    callbacks: {{
                                        title: function(context) {{
                                            return 'Meta Format: ' + context[0].label;
                                        }},
                                        label: function(context) {{
                                            const value = context.parsed.y;
                                            if (isNormalized) {{
                                                return context.dataset.label + ': ' + (value * 100).toFixed(1) + '%';
                                            }} else {{
                                                return context.dataset.label + ': ' + value + ' occurrences';
                                            }}
                                        }}
                                    }}
                                }}
                            }},
                            layout: {{
                                padding: {{
                                    top: 10,
                                    right: 10,
                                    bottom: 60, // Increased bottom padding for legend
                                    left: 10
                                }}
                            }}
                        }}
                    }});
                    
                    // Store chart reference for cleanup
                    window.cardOccurrenceChartInstances = window.cardOccurrenceChartInstances || {{}};
                    window.cardOccurrenceChartInstances[chartId] = chart;
                    
                    return chart;
                }}
                
                // Create the chart
                createChart();
            }})();
        """),
        style="height: 400px; width: 100%;",
        cls="bg-gray-800/30 rounded-lg p-4"
    ) 