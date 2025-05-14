from fasthtml import ft
from typing import Any, List
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
                        }}
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