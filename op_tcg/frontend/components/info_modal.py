from fasthtml import ft

def create_info_modal(title: str, message: str, primary_button_text: str = None, primary_button_url: str = None, secondary_button_text: str = "Close", icon_type: str = "info") -> ft.Div:
    """
    Create a reusable generic info modal.

    Args:
        title: Modal title
        message: Content message
        primary_button_text: Text for primary action button (optional)
        primary_button_url: URL/Action for primary button
        secondary_button_text: Text for close/secondary button
        icon_type: "info", "warning", "error", "success" - determines icon and color
    """

    # Define colors and icons based on type
    colors = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "success": "green"
    }
    color = colors.get(icon_type, "blue")

    # SVG Icons
    icons = {
        "info": '<path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm-1-11v6h2v-6h-2zm0-4v2h2V7h-2z"/>',
        "error": '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>',
        # ... others can be added
    }
    icon_svg = icons.get(icon_type, icons["info"])

    buttons = []

    # Secondary/Close button
    buttons.append(
        ft.Button(
            secondary_button_text,
            type="button",
            onclick="document.getElementById('generic-info-modal').remove()",
            cls="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-gray-700 text-base font-medium text-gray-300 hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
        )
    )

    # Primary button
    if primary_button_text:
        action_attr = {}
        if primary_button_url:
            if primary_button_url.startswith('javascript:'):
                 action_attr['onclick'] = primary_button_url.replace('javascript:', '')
            else:
                 action_attr['onclick'] = f"window.location.href='{primary_button_url}'"

        buttons.append(
            ft.Button(
                primary_button_text,
                type="button",
                cls=f"w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-{color}-600 text-base font-medium text-white hover:bg-{color}-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-{color}-500 sm:ml-3 sm:w-auto sm:text-sm mb-2 sm:mb-0",
                **action_attr
            )
        )
        # Reorder to put primary right (standard web convention)
        buttons.reverse()

    return ft.Div(
        ft.Div(
            ft.Div(
                ft.Div(
                    ft.Div(
                        # Icon
                        ft.Div(
                            ft.Svg(
                                ft.Safe(icon_svg),
                                viewBox="0 0 24 24",
                                fill="currentColor",
                                cls=f"h-6 w-6 text-{color}-600"
                            ),
                            cls=f"mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-{color}-100/10 sm:mx-0 sm:h-10 sm:w-10"
                        ),
                        # Content
                        ft.Div(
                            ft.H3(title, cls="text-lg leading-6 font-medium text-white", id="modal-title"),
                            ft.Div(
                                ft.P(message, cls="text-sm text-gray-400"),
                                cls="mt-2"
                            ),
                            cls="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left"
                        ),
                        cls="sm:flex sm:items-start"
                    ),
                    # Buttons
                    ft.Div(
                        *buttons,
                        cls="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse"
                    ),
                    cls="inline-block align-bottom bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6"
                ),
            ),
            cls="fixed inset-0 bg-black bg-opacity-75 transition-opacity flex items-center justify-center z-[100]"
        ),
        id="generic-info-modal",
        onclick="if(event.target.id === 'generic-info-modal') this.remove();", # Click backdrop to close
        style="z-index: 100;" # Explicit inline style to guarantee z-index behavior
    )


