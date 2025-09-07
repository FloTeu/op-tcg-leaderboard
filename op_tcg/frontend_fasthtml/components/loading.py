from fasthtml import ft

def create_loading_spinner(id: str = None, size: str = "w-8 h-8", container_classes: str = "", is_htmx_indicator: bool = True):
    """Creates a loading spinner with customizable size and container classes.
    
    Args:
        id: Optional ID for the loading indicator
        size: Tailwind size classes for the spinner (default: "w-8 h-8")
        container_classes: Additional classes for the container div
        is_htmx_indicator: Whether this spinner should be an HTMX indicator (default: True)
    """
    spinner_div = ft.Div(
        # Outer ring
        ft.Div(
            cls=f"absolute {size} border-4 border-gray-700 rounded-full"
        ),
        # Spinning ring
        ft.Div(
            cls=f"absolute {size} border-4 border-blue-400 rounded-full animate-spin",
            style="border-top-color: transparent"
        ),
        cls=f"relative {size}"
    )
    
    # Create a wrapper div that's always centered
    centered_wrapper = ft.Div(
        spinner_div,
        cls="flex items-center justify-center w-full h-full"
    )
    
    # Add htmx-indicator class to the outer container if needed
    htmx_class = " htmx-indicator" if is_htmx_indicator else ""
    container_classes = f"w-full h-full flex items-center justify-center{htmx_class} {container_classes}"
    
    container = ft.Div(
        centered_wrapper,
        cls=container_classes.strip(),
        id=id
    )
    
    return container

def create_loading_overlay(id: str = None, size: str = "w-8 h-8"):
    """Creates a loading spinner with a semi-transparent overlay background.
    
    Args:
        id: Optional ID for the loading indicator
        size: Tailwind size classes for the spinner
    """
    return create_loading_spinner(
        id=id,
        size=size,
        container_classes="absolute inset-0 bg-gray-900/50",
        is_htmx_indicator=True
    ) 


def create_skeleton_cards_indicator(id: str = None, count: int = 12, grid_cls: str | None = None) -> ft.Div:
    """Generic skeleton loader showing a grid of card-like placeholders.

    Args:
        id: Optional ID for the skeleton container
        count: Number of skeleton tiles
        grid_cls: Tailwind grid classes; defaults to a responsive grid
    """
    grid_cls = grid_cls or "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4"

    def _tile():
        return ft.Div(
            # Image placeholder
            ft.Div(cls="w-full h-40 rounded-t-lg skeleton skeleton-animate"),
            # Text placeholder area
            ft.Div(
                ft.Div(cls="h-4 w-3/4 mb-2 rounded skeleton skeleton-animate"),
                ft.Div(cls="h-3 w-1/2 rounded skeleton skeleton-animate"),
                cls="p-2"
            ),
            cls="bg-gray-800 rounded-lg overflow-hidden"
        )

    tiles = [_tile() for _ in range(count)]

    # The container has htmx-indicator so it shows only during requests
    return ft.Div(
        ft.Div(*tiles, cls=grid_cls),
        cls="htmx-indicator w-full",
        id=id
    )