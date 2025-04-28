from fasthtml import ft
from .sidebar import sidebar

def layout(content):
    return ft.Div(
        # Add JavaScript for sidebar functionality
        ft.Script("""
            function toggleSidebar() {
                const sidebar = document.getElementById('sidebar');
                const mainContent = document.getElementById('main-content');
                const burgerMenu = document.getElementById('burger-menu');
                const topBar = document.getElementById('top-bar');
                
                if (sidebar.style.transform === 'translateX(-100%)') {
                    sidebar.style.transform = 'translateX(0)';
                    mainContent.style.marginLeft = '256px';
                    burgerMenu.style.left = '2px';
                    topBar.style.display = 'none';
                } else {
                    sidebar.style.transform = 'translateX(-100%)';
                    mainContent.style.marginLeft = '0';
                    burgerMenu.style.left = '8px';
                    topBar.style.display = 'flex';
                }
            }
        """),
        # Top bar that appears when sidebar is collapsed
        ft.Div(
            ft.Div(
                ft.Button(
                    "☰",
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="burger-menu"
                ),
                cls="flex items-center h-16 px-4"
            ),
            cls="fixed top-0 left-0 right-0 bg-gray-900",
            id="top-bar",
            style="display: none;"
        ),
        sidebar(),
        ft.Div(
            content,
            cls="p-8 ml-64 min-h-screen bg-gray-900 transition-all duration-300 ease-in-out mt-16",
            id="main-content"
        ),
        cls="relative bg-gray-900"
    ) 