from fasthtml import ft

def sidebar_content():
    return ft.Div(
        ft.Div(
            ft.H2("Navigation", cls="text-xl font-bold mb-4 text-white"),
            ft.Div(
                ft.Button("Home", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/'"),
                ft.Button("Page 1", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page1'"),
                ft.Button("Page 2", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page2'"),
                ft.Button("Settings", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/settings'"),
                cls="space-y-2"
            ),
            cls="p-4 mt-8"
        ),
        cls="relative"
    )

def sidebar():
    return ft.Div(
        # Sidebar with burger menu inside
        ft.Div(
            ft.Div(
                ft.Button(
                    "☰",
                    variant="ghost",
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="burger-menu"
                ),
                cls="absolute right-2 top-2"
            ),
            sidebar_content(),
            cls="w-64 bg-gray-800 h-screen fixed left-0 top-0 transition-all duration-300 ease-in-out",
            id="sidebar"
        )
    ) 