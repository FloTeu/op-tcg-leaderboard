# A web app using the shad4fast library

from fasthtml import ft
from fasthtml.common import fast_app, serve
from shad4fast import * # Or individual components: Button, Input etc.

# Create main app
app, rt, todos, Todo = fast_app(
    'data/todos.db',
    hdrs=[
        ft.Style(':root { --pico-font-size: 100%; }'),
        ft.Link(
            href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            rel="stylesheet"
        )
    ],
    id=int, title=str, done=bool, pk='id')

# Define some example data
example_data = {
    "sales": 12456,
    "users": 8234,
    "conversion": 23.4
}

@rt("/")
def dashboard():
    return ft.Div(
        # Sidebar
        ft.Div(
            ft.Div(
                ft.H2("Navigation", cls="text-xl font-bold mb-4 text-white"),
                ft.Div(
                    Button("Dashboard", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700"),
                    Button("Analytics", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700"),
                    Button("Settings", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700"),
                    cls="space-y-2"
                ),
                ft.Div(
                    ft.H2("Filters", cls="text-xl font-bold mb-4 mt-8 text-white"),
                    Select(
                        placeholder="Select time period",
                        options=[
                            {"label": "Last 24 hours", "value": "24h"},
                            {"label": "Last 7 days", "value": "7d"},
                            {"label": "Last 30 days", "value": "30d"},
                        ],
                        cls="w-full bg-gray-700 text-white"
                    ),
                    cls="mt-4"
                ),
                cls="p-4"
            ),
            cls="w-64 bg-gray-800 h-screen fixed left-0 top-0"
        ),
        
        # Main content
        ft.Div(
            # Header section
            ft.Div(
                ft.H1("Dashboard", cls="text-3xl font-bold text-white"),
                ft.P("Welcome to your analytics dashboard", cls="text-gray-400"),
                cls="space-y-4"
            ),
            
            # Stats cards
            ft.Div(
                Card(
                    CardHeader(ft.Div("Total Sales", cls="text-sm font-medium text-white")),
                    CardContent(ft.Div(f"${example_data['sales']:,}", cls="text-2xl font-bold text-white")),
                    title="Total Sales",
                    cls="bg-gray-800"
                ),
                Card(
                    CardHeader(ft.Div("Active Users", cls="text-sm font-medium text-white")),
                    CardContent(ft.Div(f"{example_data['users']:,}", cls="text-2xl font-bold text-white")),
                    title="Active Users",
                    cls="bg-gray-800"
                ),
                Card(
                    CardHeader(ft.Div("Conversion Rate", cls="text-sm font-medium text-white")),
                    CardContent(ft.Div(f"{example_data['conversion']}%", cls="text-2xl font-bold text-white")),
                    title="Conversion Rate",
                    cls="bg-gray-800"
                ),
                cls="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6"
            ),
            
            # Interactive section
            ft.Div(
                Card(
                    CardHeader(ft.Div("Data Filter", cls="font-medium text-white")),
                    CardContent(
                        ft.Div(
                            Select(
                                placeholder="Select time period",
                                options=[
                                    {"label": "Last 24 hours", "value": "24h"},
                                    {"label": "Last 7 days", "value": "7d"},
                                    {"label": "Last 30 days", "value": "30d"},
                                ],
                                cls="bg-gray-700 text-white"
                            ),
                            ft.Div(
                                Button("Update", variant="default", cls="bg-blue-600 hover:bg-blue-700 text-white"),
                                Button("Reset", variant="outline", cls="text-white border-gray-600 hover:bg-gray-700"),
                                cls="flex space-x-2"
                            ),
                            cls="space-y-4"
                        )
                    ),
                    title="Data Filter",
                    cls="bg-gray-800"
                ),
                cls="mt-8 space-y-4"
            ),
            
            # Example chart placeholder
            ft.Div(
                Card(
                    CardHeader(ft.Div("Revenue Over Time", cls="font-medium text-white")),
                    CardContent(
                        ft.Div(
                            ft.Div("Chart Placeholder", cls="text-gray-400"),
                            cls="h-[300px] flex items-center justify-center bg-gray-700 rounded-lg"
                        )
                    ),
                    title="Revenue Over Time",
                    cls="bg-gray-800"
                ),
                cls="mt-8"
            ),
            cls="p-8 ml-64 min-h-screen bg-gray-900"  # Dark background for main content
        ),
        cls="relative bg-gray-900"  # Dark background for the whole page
    )

serve()
