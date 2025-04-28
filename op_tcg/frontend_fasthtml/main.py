
from dotenv import load_dotenv
load_dotenv()

from fasthtml import ft
from fasthtml.common import fast_app, serve
from starlette.requests import Request
from op_tcg.frontend_fasthtml.components.layout import layout
from op_tcg.frontend_fasthtml.pages.home import home_page
from op_tcg.frontend_fasthtml.pages.page1 import page1_content
from op_tcg.frontend_fasthtml.pages.page2 import page2_content
from op_tcg.frontend_fasthtml.pages.settings import settings_content
from op_tcg.frontend_fasthtml.api.routes import setup_api_routes

# Create main app
app, rt = fast_app(
    pico=False,
    hdrs=[
        ft.Style(':root { --pico-font-size: 100%; }'),
        ft.Style('body { background-color: rgb(17, 24, 39); }'),
        ft.Link(
            href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            rel="stylesheet"
        )
    ],
    static_path='op_tcg/frontend_fasthtml/'
)

# Setup API routes
setup_api_routes(rt)

# Home page
@rt("/")
def home():
    return layout(home_page())

# Page 1
@rt("/page1")
def page1():
    return layout(page1_content())

# Page 2
@rt("/page2")
def page2():
    return layout(page2_content())

# Settings page
@rt("/settings")
def settings():
    return layout(settings_content())

if __name__ == "__main__":
    serve()
