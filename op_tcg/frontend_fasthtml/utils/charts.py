from fasthtml import ft
from typing import Any, List, Dict
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
import json

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
                            tooltip: {{
                                enabled: false,  // Disable default tooltip
                            }},
                            subtitle: {{
                                display: true,
                                text: 'Size of the bubbles increases with the tournament wins',
                                color: 'rgba(255, 255, 255, 0.7)',
                                font: {{ size: 12, style: 'italic' }},
                                padding: {{ 
                                    bottom: 10
                                }}
                            }}
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
                            subtitle: {
                                display: true,
                                text: 'Size of the bubbles increases with the tournament wins',
                                color: 'rgba(255, 255, 255, 0.7)',
                                font: { size: 12, style: 'italic' },
                                padding: {
                                    bottom: 10
                                }
                            }
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
                
                // Clean up old tooltip if it exists
                const oldTooltip = document.getElementById('chartjs-tooltip');
                if (oldTooltip) {{
                    oldTooltip.remove();
                }}
                
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
                
                const data = {data_json};
                const colors = {colors_json};
                
                // Add transparency to colors
                const transparentColors = colors.map(color => {{
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
                            data: data,
                            backgroundColor: transparentColors,
                            borderColor: colors,
                            borderWidth: 1,
                            hoverBackgroundColor: colors,
                            radius: (context) => {{
                                // Get the bubble size from the data
                                return context.raw.r;
                            }}
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '{title}',
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
                            const tooltipEl = document.getElementById('chartjs-tooltip');
                            
                            if (!tooltipEl) {{
                                const div = document.createElement('div');
                                div.id = 'chartjs-tooltip';
                                document.body.appendChild(div);
                            }}
                            
                            if (!chartElements || chartElements.length === 0) {{
                                tooltipEl.style.opacity = 0;
                                return;
                            }}
                            
                            const element = chartElements[0];
                            const data = element.element.$context.raw;
                            
                            // Create tooltip content with flex layout
                            const tooltipContent = `
                                <div style="
                                    display: flex;
                                    gap: 16px;
                                    min-width: 400px;
                                    height: 150px;
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
                                        padding: 12px 16px 12px 0;
                                        display: flex;
                                        flex-direction: column;
                                        justify-content: center;
                                    ">
                                        <div style="font-weight: bold; margin-bottom: 12px; font-size: 1.2em; white-space: normal;">${{data.name}}</div>
                                        <div style="margin: 4px 0;">Win Rate: ${{(data.y * 100).toFixed(1)}}%</div>
                                        <div style="margin: 4px 0;">Tournaments: ${{data.x}}</div>
                                        <div style="margin: 4px 0;">Tournament Wins: ${{data.raw_wins}}</div>
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
                            
                            // Position the tooltip
                            const position = element.element.tooltipPosition();
                            const chartPosition = container.getBoundingClientRect();
                            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                            
                            tooltipEl.style.left = (chartPosition.left + scrollLeft + position.x) + 'px';
                            tooltipEl.style.top = (chartPosition.top + scrollTop + position.y - 10) + 'px';
                        }},
                        scales: {{
                            x: {{
                                type: 'logarithmic',
                                title: {{
                                    display: true,
                                    text: 'Number of Tournament Matches',
                                    color: 'white'
                                }},
                                ticks: {{
                                    color: '{ChartColors.TICK_TEXT}',
                                    font: {{
                                        size: 10
                                    }},
                                    padding: 5
                                }},
                                grid: {{
                                    color: 'rgba(255, 255, 255, 0.1)'
                                }}
                            }},
                            y: {{
                                title: {{
                                    display: true,
                                    text: 'Win Rate',
                                    color: 'white'
                                }},
                                ticks: {{
                                    color: '{ChartColors.TICK_TEXT}',
                                    font: {{
                                        size: 10
                                    }},
                                    padding: 5,
                                    callback: function(value) {{
                                        return (value * 100).toFixed(0) + '%';
                                    }}
                                }},
                                grid: {{
                                    color: 'rgba(255, 255, 255, 0.1)'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Clean up on HTMX request
                container.addEventListener('htmx:beforeSwap', function() {{
                    const tooltipEl = document.getElementById('chartjs-tooltip');
                    if (tooltipEl) {{
                        tooltipEl.remove();
                    }}
                    if (chart) {{
                        chart.destroy();
                    }}
                }});
            }})();
        """),
        style="height: 600px; width: 100%;"  # Explicit height and width
    ) 