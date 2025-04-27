from fasthtml.common import *

# Create the FastHTML application
app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(rel='stylesheet', href='/op_tcg/frontend/fasthtml/assets/sidebar.css', type='text/css'),
    ), live=True)

# Sidebar component
def sidebar(is_collapsed=False):
    toggle_button = Button("Toggle", id="toggle-btn", hx_trigger="click", hx_target="#sidebar", hx_swap="outerHTML", cls="toggle-button")
    sidebar_content = Div(
        H1("My Sidebar", cls="sidebar-title"),
        Ul(
            Li(A("Home", href="/")),
            Li(A("About", href="/about")),
            Li(A("Contact", href="/contact")),
        ),
        cls="sidebar-content"
    )
    sidebar_div = Div(sidebar_content, id="sidebar", cls="sidebar" + (" collapsed" if is_collapsed else ""))
    return Div(toggle_button, sidebar_div, cls="sidebar-container")

# Main content component
def main_content():
    return Div(
        H2("Welcome to the Main Content Area"),
        P("This is where your main content will go."),
        cls="main-content"
    )

# Home route
@rt("/")
def home():
    return  Div(sidebar(), main_content(), cls="container")

# About route
@rt("/about")
def about():
    return Div(sidebar(), Div(H2("About Page"), P("Information about the app."), cls="main-content"), cls="container")

# Contact route
@rt("/contact")
def contact():
    return Div(sidebar(), Div(H2("Contact Page"), P("Get in touch with us."), cls="main-content"), cls="container")

# Serve the application
serve()

