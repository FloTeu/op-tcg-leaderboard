from fasthtml import ft


_SIDEBAR_STYLES = ft.Style("""
    #sidebar {
        background: #0d1424;
        border-right: 1px solid #1a2540;
    }
    #sidebar::-webkit-scrollbar { width: 3px; }
    #sidebar::-webkit-scrollbar-track { background: transparent; }
    #sidebar::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }

    .sb-title {
        font-family: 'Bebas Neue', sans-serif;
        color: #f1f5f9;
        letter-spacing: 0.08em;
        font-size: 1.1rem;
    }
    .sb-section-label {
        font-family: 'Bebas Neue', sans-serif;
        color: #475569;
        letter-spacing: 0.12em;
        font-size: .72rem;
        padding: 6px 14px 4px;
        display: block;
    }
    .sb-link {
        display: flex;
        align-items: center;
        padding: 8px 14px;
        border-radius: 8px;
        border-left: 3px solid transparent;
        font-family: 'Barlow', sans-serif;
        font-size: .875rem;
        font-weight: 400;
        color: #94a3b8;
        transition: background .15s, color .15s, border-color .15s;
        cursor: pointer;
        text-decoration: none;
    }
    .sb-link:hover {
        background: rgba(245,158,11,.06);
        color: #cbd5e1;
        border-left-color: rgba(245,158,11,.25);
    }
    .sb-link-active {
        display: flex;
        align-items: center;
        padding: 8px 14px;
        border-radius: 8px;
        border-left: 3px solid #f59e0b;
        background: rgba(245,158,11,.12);
        color: #f59e0b;
        font-family: 'Barlow', sans-serif;
        font-size: .875rem;
        font-weight: 600;
        text-decoration: none;
        transition: background .15s;
    }
    .sb-burger {
        background: #1a2540;
        border: none;
        border-radius: 6px;
        padding: 8px;
        cursor: pointer;
        transition: background .15s;
        line-height: 0;
    }
    .sb-burger:hover { background: #2d3f5a; }

    .sb-section { margin-bottom: 24px; }

    .sb-filter-label {
        font-family: 'Bebas Neue', sans-serif;
        color: #f1f5f9;
        letter-spacing: 0.1em;
        font-size: 1rem;
        margin-bottom: 12px;
        padding-top: 12px;
        display: block;
    }
""")


def create_nav_link(href: str | None, text: str, icon, is_active: bool = False):
    cls = "sb-link-active" if is_active else "sb-link"
    icon_el = icon if not isinstance(icon, str) else ft.Span(icon, style="margin-right:10px;font-size:.95rem;")
    content = ft.Div(
        icon_el,
        ft.Span(text),
        cls=cls,
    )
    if href:
        return ft.A(content, href=href, cls="block")
    else:
        return ft.Div(content, cls="block cursor-default")


def create_nav_section(title: str, links: list[tuple[str | None, str, str, bool]]) -> ft.Div:
    return ft.Div(
        ft.Span(title, cls="sb-section-label"),
        *[create_nav_link(href, text, icon, is_active) for href, text, icon, is_active in links],
        cls="sb-section",
    )


def sidebar_content(filter_component=None, current_path="/", persist_query: dict | None = None):
    def build_href(base_path: str) -> str:
        if not persist_query:
            return base_path
        query_params = {}
        if persist_query.get("region"):
            query_params["region"] = persist_query.get("region")
        if persist_query.get("meta_format"):
            query_params["meta_format"] = persist_query.get("meta_format")
        if not query_params:
            return base_path
        qp = "&".join([f"{k}={v}" for k, v in query_params.items() if v is not None and v != ""])
        return f"{base_path}?{qp}" if qp else base_path

    leader_links = [
        (build_href("/"), "Leaderboard", ft.Img(src="/public/favicon32x23.png", style="width:18px;height:auto;margin-right:10px;flex-shrink:0;vertical-align:middle;"), current_path == "/"),
        (build_href("/leader"), "Leader", "👤", current_path == "/leader"),
        (build_href("/meta"), "Meta Analysis", "📊", current_path == "/meta"),
        (build_href("/tournaments"), "Tournaments", "🏅", current_path == "/tournaments"),
        (build_href("/card-movement"), "Card Movement", "📈", current_path == "/card-movement"),
        (build_href("/matchups"), "Matchups", "🥊", current_path == "/matchups"),
    ]

    card_links = [
        (build_href("/card-popularity"), "Card Popularity", "💃", current_path == "/card-popularity"),
    ]

    tool_links = [
        ("/deckbuilder", "Deck Builder", "🃏", current_path == "/deckbuilder"),
        ("/watchlist", "Watchlist", "❤️", current_path == "/watchlist"),
    ]

    return ft.Div(
        create_nav_section("Leader", leader_links),
        create_nav_section("Card", card_links),
        create_nav_section("Tools", tool_links),
        ft.Div(
            ft.Span("Filters", cls="sb-filter-label") if filter_component else None,
            filter_component if filter_component else None,
            cls="mt-4"
        ) if filter_component else None,
        cls="space-y-1",
    )


def sidebar(filter_component=None, current_path="/", persist_query: dict | None = None):
    burger_lines = ft.Div(
        ft.Div(style="width:20px;height:2px;background:#94a3b8;margin-bottom:5px;border-radius:1px;"),
        ft.Div(style="width:20px;height:2px;background:#94a3b8;margin-bottom:5px;border-radius:1px;"),
        ft.Div(style="width:20px;height:2px;background:#94a3b8;border-radius:1px;"),
        style="display:flex;flex-direction:column;justify-content:center;align-items:center;",
    )
    return ft.Div(
        _SIDEBAR_STYLES,
        ft.Div(
            ft.Div(
                ft.Span("Navigation", cls="sb-title"),
                ft.Button(
                    burger_lines,
                    cls="sb-burger",
                    onclick="toggleSidebar()",
                    id="sidebar-burger-menu",
                ),
                style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;",
            ),
            sidebar_content(filter_component, current_path, persist_query),
            cls="p-4",
        ),
        cls="fixed left-0 top-0 h-full w-80 overflow-y-auto z-50 shadow-lg",
        id="sidebar",
        style="transform: translateX(-100%);",
    )
