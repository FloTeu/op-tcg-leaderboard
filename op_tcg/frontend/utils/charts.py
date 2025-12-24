from fasthtml import ft
from typing import Any, List, Dict
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
import json
import time

# ======================================================================================
# CHART CREATION FUNCTIONS - REFACTORED TO USE CHARTMANAGER
# ======================================================================================
# These functions now use the ChartManager class from charts.js instead of embedding
# large amounts of JavaScript code directly in Python f-strings. This approach provides:
#
# 1. BETTER SEPARATION OF CONCERNS: Python handles data preparation, JS handles visualization
# 2. IMPROVED MAINTAINABILITY: JavaScript code can be properly formatted and debugged
# 3. REDUCED MEMORY USAGE: Less string interpolation and more efficient chart management
# 4. ENVIRONMENTAL BENEFITS: More efficient code generation and execution
# 5. REUSABILITY: ChartManager can be used across different parts of the application
# ======================================================================================

def _create_chart_script(chart_type: str, container_id: str, config: dict) -> ft.Script:
    """Ultra-simple chart creation that works with HTMX."""
    # Add containerId to config
    config_with_id = {'containerId': container_id, **config}
    config_json = json.dumps(config_with_id)
    
    return ft.Script(f"""
        (function() {{
            // Wait for HTMX to fully settle before creating chart
            setTimeout(function() {{
                const container = document.getElementById('{container_id}');
                if (!container) return;
                
                if (window.chartManager && window.chartManager.{chart_type}) {{
                    window.chartManager.{chart_type}({config_json});
                }}
            }}, 100); // Give HTMX time to settle
        }})();
    """)

def create_line_chart(container_id: str, data: List[dict[str, Any]], 
                     y_key: str = "winRate", x_key: str = "meta", 
                     y_label: str = "Win Rate", y_suffix: str = "%",
                     color: ChartColors = ChartColors.NEUTRAL,
                     show_x_axis: bool = True,
                     show_y_axis: bool = True) -> ft.Div:
    """
    Creates a line chart using Chart.js ChartManager (REFACTORED)

    This function now uses the ChartManager class from charts.js instead of 
    embedding JavaScript directly in Python f-strings. Benefits:
    - Cleaner separation of concerns (Python for data, JS for charts)
    - Better maintainability and debugging
    - More efficient memory usage
    - Environmental friendly approach with less string interpolation

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
    # Prepare configuration for ChartManager
    config = {
        'containerId': container_id,
        'data': data,
        'yKey': y_key,
        'xKey': x_key,
        'ySuffix': y_suffix,
        'color': str(color),
        'showXAxis': show_x_axis,
        'showYAxis': show_y_axis
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"  # Use full height and width
        ),
        _create_chart_script('createLineChart', container_id, config),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    )

def create_leader_win_rate_radar_chart(container_id: str, data: List[dict[str, Any]], 
                                      leader_ids: List[str], colors: List[str] = None, 
                                      show_legend: bool = True) -> ft.Div:
    """
    Create a radar chart to display leader win rates against different color matchups (REFACTORED).

    This function now uses the ChartManager class from charts.js instead of 
    embedding JavaScript directly in Python f-strings. Benefits:
    - Cleaner separation of concerns (Python for data, JS for charts)
    - Better maintainability and debugging
    - More efficient memory usage
    - Environmental friendly approach with less string interpolation

    Args:
        container_id: HTML ID for the chart container
        data: Radar chart data with color matchups
        leader_ids: List of leader IDs to include in the chart
        colors: List of colors for each leader (optional)
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

    # Prepare configuration for ChartManager
    config = {
        'containerId': container_id,
        'data': filtered_data,
        'leaderIds': leader_ids,
        'colors': colors,
        'showLegend': show_legend
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        _create_chart_script('createRadarChart', container_id, config),
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
    Creates a bar chart using Chart.js ChartManager (REFACTORED)

    This function now uses the ChartManager class from charts.js instead of 
    embedding JavaScript directly in Python f-strings. Benefits:
    - Cleaner separation of concerns (Python for data, JS for charts)
    - Better maintainability and debugging
    - More efficient memory usage
    - Environmental friendly approach with less string interpolation

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
    # Prepare configuration for ChartManager
    config = {
        'containerId': container_id,
        'data': data,
        'yKey': y_key,
        'xKey': x_key,
        'ySuffix': y_suffix,
        'color': str(color),
        'showXAxis': show_x_axis,
        'showYAxis': show_y_axis
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        _create_chart_script('createBarChart', container_id, config),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    )

def create_stream_chart(container_id: str, data: List[dict[str, Any]],
                       y_key: str = "wins", x_key: str = "date",
                       y_label: str = "Tournament Wins", y_suffix: str = " wins",
                       color: str = ChartColors.POSITIVE,
                       show_x_axis: bool = True,
                       show_y_axis: bool = True) -> ft.Div:
    """
    Creates a stream chart using Chart.js with gradient fill and smooth transitions (REFACTORED).
    Also includes a bar chart overlay for individual data points.

    This function now uses the ChartManager class from charts.js instead of
    embedding JavaScript directly in Python f-strings. Benefits:
    - Cleaner separation of concerns (Python for data, JS for charts)
    - Better maintainability and debugging
    - More efficient memory usage
    - Environmental friendly approach with less string interpolation

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
    # Prepare configuration for ChartManager
    config = {
        'containerId': container_id,
        'data': data,
        'yKey': y_key,
        'xKey': x_key,
        'ySuffix': y_suffix,
        'color': str(color),
        'showXAxis': show_x_axis,
        'showYAxis': show_y_axis,
        'tooltipBg': str(ChartColors.TOOLTIP_BG),
        'tooltipBorder': str(ChartColors.TOOLTIP_BORDER)
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id),
            cls="h-full w-full"  # Use full height and width
        ),
        _create_chart_script('createStreamChart', container_id, config),
        style="height: 120px; width: 100%;"  # Explicit height in style attribute
    )

def create_bubble_chart(container_id: str, data: List[Dict[str, Any]], colors: List[str], 
                        title: str = "Leader Tournament Popularity") -> ft.Div:
    """
    Create a bubble chart for leader tournament statistics (REFACTORED).

    This function now uses the ChartManager class from charts.js instead of 
    embedding JavaScript directly in Python f-strings. Benefits:
    - Cleaner separation of concerns (Python for data, JS for charts)
    - Better maintainability and debugging
    - More efficient memory usage
    - Environmental friendly approach with less string interpolation

    Args:
        container_id: Unique ID for the chart container
        data: List of dictionaries containing the data points
        colors: List of color strings for each bubble
        title: Chart title
    """
    # Prepare configuration for ChartManager
    config = {
        'containerId': container_id,
        'data': data,
        'colors': colors,
        'title': title,
        'tooltipBg': str(ChartColors.TOOLTIP_BG),
        'tooltipBorder': str(ChartColors.TOOLTIP_BORDER),
        'tickTextColor': str(ChartColors.TICK_TEXT)
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"  # Use full height and width
        ),
        _create_chart_script('createBubbleChart', container_id, config),
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

                            // Create tooltip content with flex layout - responsive for mobile
                            const isMobile = window.innerWidth <= 640;
                            const tooltipContent = `
                                <div style="
                                    display: flex;
                                    gap: ${{isMobile ? '8px' : '16px'}};
                                    min-width: ${{isMobile ? '240px' : '300px'}};
                                    max-width: ${{isMobile ? '90vw' : '400px'}};
                                    height: ${{isMobile ? '100px' : '120px'}};
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
                                        padding: ${{isMobile ? '8px 12px 8px 0' : '12px 16px 12px 0'}};
                                        display: flex;
                                        flex-direction: column;
                                        justify-content: center;
                                    ">
                                        <div style="font-weight: bold; margin-bottom: ${{isMobile ? '8px' : '12px'}}; font-size: ${{isMobile ? '1em' : '1.2em'}}; white-space: normal;">${{label}}</div>
                                        <div style="margin: ${{isMobile ? '2px 0' : '4px 0'}}; font-size: ${{isMobile ? '0.9em' : '1em'}};">Count: ${{value}}</div>
                                        <div style="margin: ${{isMobile ? '2px 0' : '4px 0'}}; font-size: ${{isMobile ? '0.9em' : '1em'}};">Percentage: ${{pct}}%</div>
                                        ${{colorIndicators ? `<div style="margin: ${{isMobile ? '4px 0 2px 0' : '8px 0 4px 0'}}; font-size: ${{isMobile ? '0.85em' : '0.9em'}};"><strong>Colors:</strong></div><div style="margin: ${{isMobile ? '2px 0' : '4px 0'}};">${{colorIndicators}}</div>` : ''}}
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
                            tooltipEl.style.boxSizing = 'border-box';

                            // Position the tooltip with bounds checking for mobile
                            try {{
                                const canvasPosition = canvas.getBoundingClientRect();
                                const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                const viewportWidth = window.innerWidth;

                                if (canvasPosition && tooltipEl) {{
                                    let tooltipLeft = canvasPosition.left + scrollLeft + event.x;
                                    const tooltipTop = canvasPosition.top + scrollTop + event.y - 10;
                                    
                                    // Get tooltip width after setting content
                                    const tooltipWidth = tooltipEl.offsetWidth || (isMobile ? 240 : 300);
                                    
                                    // Ensure tooltip stays within viewport horizontally
                                    const minLeft = scrollLeft + 10; // 10px margin from left edge
                                    const maxLeft = scrollLeft + viewportWidth - tooltipWidth - 10; // 10px margin from right edge
                                    
                                    // Clamp tooltip position to stay within viewport
                                    tooltipLeft = Math.max(minLeft, Math.min(maxLeft, tooltipLeft));
                                    
                                    tooltipEl.style.left = tooltipLeft + 'px';
                                    tooltipEl.style.top = tooltipTop + 'px';
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

#
# def create_donut_chart(container_id: str, labels: List[str], values: List[int], colors: List,
#                        images: List[str], leader_ids: List[str] = None) -> ft.Div:
#     """
#     Create a donut chart for displaying data with multi-color support (REFACTORED).
#
#     This function now uses the ChartManager class from charts.js instead of
#     embedding JavaScript directly in Python f-strings. Benefits:
#     - Cleaner separation of concerns (Python for data, JS for charts)
#     - Better maintainability and debugging
#     - More efficient memory usage
#     - Environmental friendly approach with less string interpolation
#
#     Args:
#         container_id: Unique ID for the chart container
#         labels: List of labels for each segment
#         values: List of values for each segment
#         colors: List of colors (can be arrays for multi-color leaders)
#         images: List of image URLs for tooltips
#         leader_ids: List of leader IDs corresponding to each segment (for click handling)
#     """
#     # Prepare configuration for ChartManager
#     config = {
#         'containerId': container_id,
#         'labels': labels,
#         'values': values,
#         'colors': colors,
#         'images': images,
#         'leaderIds': leader_ids or labels,
#         'tooltipBg': str(ChartColors.TOOLTIP_BG),
#         'tooltipBorder': str(ChartColors.TOOLTIP_BORDER)
#     }
#
#     return ft.Div(
#         # Chart container with canvas
#         ft.Div(
#             ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
#             cls="h-full w-full"
#         ),
#         _create_chart_script('createDonutChart', container_id, config),
#         style="height: 340px; width: 100%;"
#     )

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
    
    # Prepare config for JavaScript ChartManager
    config = {
        'data': normalized_data,
        'metaFormats': meta_formats,
        'leaders': filtered_leaders,
        'colors': color_palette[:len(filtered_leaders)],
        'isNormalized': normalized,
        'cardName': card_name
    }

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
        _create_chart_script('createCardOccurrenceChart', unique_container_id, config),
        style="height: 400px; width: 100%;",
        cls="bg-gray-800/30 rounded-lg p-4"
    )


def create_price_development_chart(container_id: str, price_data: dict[str, list[dict]], card_name: str = "") -> ft.Div:
    """
    Creates a price development chart showing EUR and USD prices over time using Chart.js

    Args:
        container_id: Unique ID for the chart container
        price_data: Dictionary with 'eur' and 'usd' keys containing price history data
        card_name: Name of the card for the chart title
    """

    # Extract data for both currencies
    eur_data = price_data.get('eur', [])
    usd_data = price_data.get('usd', [])

    # Get all unique dates and sort them
    all_dates = set()
    if eur_data:
        all_dates.update(item['date'] for item in eur_data)
    if usd_data:
        all_dates.update(item['date'] for item in usd_data)

    sorted_dates = sorted(list(all_dates))

    # Create date-indexed data
    eur_price_map = {item['date']: item['price'] for item in eur_data}
    usd_price_map = {item['date']: item['price'] for item in usd_data}

    # Build chart data
    chart_data = []
    for date in sorted_dates:
        chart_data.append({
            'date': date,
            'eur_price': eur_price_map.get(date),
            'usd_price': usd_price_map.get(date)
        })

    # Prepare config for JavaScript ChartManager
    config = {
        'data': chart_data,
        'cardName': card_name
    }

    return ft.Div(
        # Chart container with canvas
        ft.Div(
            ft.Canvas(id=container_id, style="width:100%; height:100%; display:block"),
            cls="h-full w-full"
        ),
        _create_chart_script('createPriceDevelopmentChart', container_id, config),
        style="height: 300px; width: 100%;",
        cls="bg-gray-800/30 rounded-lg p-4"
    )
