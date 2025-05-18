from fasthtml import ft
from typing import Optional

def create_leader_image_cell(
    image_url: str,
    name: str,
    color: str,
    horizontal: bool = True,
    cls: str = ""
) -> ft.Div:
    """Create a table cell with a leader image and name overlay."""
    container_height = "120px" if horizontal else "200px"
    
    return ft.Div(
        ft.Div(
            ft.Span(
                name,
                cls="text-white font-bold text-lg drop-shadow-lg"
            ),
            cls=f"absolute bottom-0 right-0 p-2 z-10"
        ),
        style=f"""
            background-image: linear-gradient(to top, {color}, transparent), url('{image_url}');
            background-size: cover, 125%;
            background-position: bottom, center {'-50px' if horizontal else '0px'};
            background-repeat: no-repeat;
            height: {container_height};
            width: 100%;
            position: relative;
        """,
        cls=f"rounded-lg overflow-hidden {cls}"
    )

def create_win_rate_cell(
    win_rate: float | None,
    tooltip: Optional[str] = None,
    max_value: float = 100.0,
    min_value: float = 0.0
) -> ft.Td:
    """Create a table cell with color-coded win rate and optional tooltip."""
    if win_rate is None:
        bg_color = "black"  # Set background to black if win_rate is None
        cell_text = "NaN"
    else:
        # Calculate color based on win rate
        mid_point = (max_value + min_value) / 2
        intensity = abs(win_rate - mid_point) / (max_value - mid_point)
        opacity = 0.3 + (intensity * 0.7)  # Scale opacity between 0.3 and 1.0
        
        if win_rate >= mid_point:
            bg_color = f"rgba(34, 197, 94, {opacity})"  # Green
        else:
            bg_color = f"rgba(239, 68, 68, {opacity})"  # Red

        cell_text = f"{win_rate:.1f}%",
        
    content = ft.Span(
        cell_text,
        cls="text-lg font-bold text-gray-900"
    )
    
    attrs = {}
    if tooltip:
        attrs["data-tooltip"] = tooltip
    
    return ft.Td(
        content,
        style=f"background-color: {bg_color};",
        cls="p-4 text-center transition-colors duration-200",
        **attrs
    ) 