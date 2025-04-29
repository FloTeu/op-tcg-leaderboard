from fasthtml import ft

def sidebar_content(filter_component=None):
    return ft.Div(
        ft.Div(
            ft.Div(
                ft.Button("Home", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/'"),
                ft.Button("Page 1", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page1'"),
                ft.Button("Page 2", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page2'"),
                ft.Button("Settings", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/settings'"),
                cls="space-y-2 mb-8"
            ),
            ft.Div(
                ft.H2("Filters", cls="text-xl font-bold text-white mb-4") if filter_component else None,
                filter_component if filter_component else None,
                cls="space-y-4"
            ),
            cls=""
        ),
        cls="relative"
    )

def sidebar(filter_component=None):
    return ft.Div(
        ft.Div(
            ft.Div(
                ft.H2("Navigation", cls="text-xl font-bold text-white"),
                ft.Button(
                    ft.Div(
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white transition-all duration-300"),
                        cls="flex flex-col justify-center items-center"
                    ),
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="sidebar-burger-menu"
                ),
                cls="flex justify-between items-center mb-4"
            ),
            sidebar_content(filter_component),
            cls="p-4"
        ),
        cls="fixed left-0 top-0 h-full w-64 bg-gray-800 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800 hover:scrollbar-thumb-gray-500",
        id="sidebar"
    ) 