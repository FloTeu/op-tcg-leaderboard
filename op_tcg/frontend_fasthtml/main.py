from fasthtml import ft
from fasthtml.common import fast_app, serve
from starlette.requests import Request
from components.layout import layout
from pages.home import home_page, create_leaderboard_table
from pages.page1 import page1_content
from pages.page2 import page2_content
from pages.settings import settings_content
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderboardSortBy
import pandas as pd

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

# API route for leaderboard
@rt("/api/leaderboard")
def api_leaderboard(request: Request):
    # Get query parameters from request
    meta_format = request.query_params.get("meta_format", MetaFormat.latest_meta_format)
    region = request.query_params.get("region", MetaFormatRegion.ALL)
    only_official = request.query_params.get("only_official", "true").lower() == "true"
    sort_by = request.query_params.get("sort_by", LeaderboardSortBy.WIN_RATE)
    
    # TODO: Replace with actual data fetching logic
    # For now, using placeholder data
    df_leader_extended = pd.DataFrame({
        "id": ["OP01-001", "OP01-002"],
        "name": ["Monkey D. Luffy", "Roronoa Zoro"],
        "meta_format": [MetaFormat.OP01, MetaFormat.OP01],
        "win_rate": [0.65, 0.60],
        "total_matches": [100, 90],
        "elo": [1500, 1450],
        "tournament_wins": [5, 3],
        "d_score": [0.75, 0.70]
    })
    
    display_name2df_col_name = {
        "Name": "name",
        "Set": "id",
        LeaderboardSortBy.TOURNAMENT_WINS: "tournament_wins",
        "Match Count": "total_matches",
        LeaderboardSortBy.WIN_RATE: "win_rate",
        LeaderboardSortBy.DOMINANCE_SCORE: "d_score",
        "Elo": "elo"
    }
    
    # Create the leaderboard table
    return create_leaderboard_table(
        df_leader_extended,
        meta_format,
        display_name2df_col_name,
        only_official
    )

if __name__ == "__main__":
    serve()
