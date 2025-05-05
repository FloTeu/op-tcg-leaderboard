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