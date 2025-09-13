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
            ft.Canvas(id=container_id),
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
        # Header with tooltip
        ft.Div(
            ft.H2(
                "Tournament Statistics Overview",
                ft.Span(
                    "ⓘ",
                    cls="ml-2 cursor-help",
                    data_tooltip="Size of the bubbles increases with the tournament wins"
                ),
                cls="text-2xl font-bold text-white mb-4 flex items-center"
            ),
            cls="mb-6"
        ),
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
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
                    
                    // Clean up old chart event listeners
                    document.removeEventListener('mouseout', hideTooltip);
                    
                    function hideTooltip() {{
                        const tooltipEl = document.getElementById('chartjs-tooltip');
                        if (tooltipEl) {{
                            tooltipEl.style.opacity = 0;
                        }}
                    }}
                    
                    // Add global mouse out listener to hide tooltip when mouse leaves chart area
                    document.addEventListener('mouseout', hideTooltip);
                    
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
                    
                    // Clear the canvas
                    const ctx = container.getContext('2d');
                    ctx.clearRect(0, 0, container.width, container.height);
                    
                    // Add transparency to colors
                    const transparentColors = chartColors.map(color => {{
                        // Convert hex to rgba with 0.7 opacity
                        const r = parseInt(color.slice(1,3), 16);
                        const g = parseInt(color.slice(3,5), 16);
                        const b = parseInt(color.slice(5,7), 16);
                        return `rgba(${{r}},${{g}},${{b}},0.7)`;
                    }});
                    
                    const chart = new Chart(container, {{
                        type: 'bubble',
                        data: {{
                            datasets: [{{
                                data: chartData,
                                backgroundColor: transparentColors,
                                borderColor: chartColors,
                                borderWidth: 1,
                                hoverBackgroundColor: chartColors,
                                radius: (context) => {{
                                    // Get the bubble size from the data
                                    return context.raw.r;
                                }}
                            }}]
                        }},
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
                                    const position = element.element.tooltipPosition();
                                    const chartPosition = container.getBoundingClientRect();
                                    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                    
                                    if (position && chartPosition && tooltipEl) {{
                                        tooltipEl.style.left = (chartPosition.left + scrollLeft + position.x) + 'px';
                                        tooltipEl.style.top = (chartPosition.top + scrollTop + position.y - 10) + 'px';
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
                        console.log('Recreating bubble chart with stored data');
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