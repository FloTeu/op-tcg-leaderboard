# op-tcg-leaderboard

One Piece TCG tournament leaderboard and analytics platform. Data is crawled from limitless-tcg.com, stored in BigQuery, and served via a FastHTML web app on GCP.

## Tech Stack

- **Backend:** Python 3.11–3.12, Poetry
- **Frontend:** python-fasthtml + HTMX, Plotly
- **Database:** Google Cloud BigQuery (analytical), Firestore (user settings)
- **Crawling:** Scrapy, Crawl4AI, BeautifulSoup4
- **Infrastructure:** GCP Cloud Run + Cloud Functions, Terraform
- **Auth:** Authlib (Google OAuth)

## Key Directories

```
op_tcg/
  backend/
    crawling/spiders/   # Scrapy spiders (limitless_tournaments, limitless_matches, limitless_prices)
    etl/                # Extract/transform/load pipelines
    models/             # Pydantic models (storage.py, matches.py, tournaments.py, cards.py, leader.py, ...)
    elo.py              # Elo rating calculation
    auth.py             # Google OAuth
    db.py               # BQ client helpers
  frontend/
    pages/              # FastHTML page handlers (home, leader, tournaments, matchups, ...)
    api/routes/         # HTMX API endpoints (filters, stats, decklists, matchups, ...)
    components/         # Reusable FastHTML components
    utils/              # cache.py, filter.py, leader_data.py, win_rate.py, ...
  cli/                  # Click CLI (etl.py, crawling.py)
  cli_app.py            # CLI entrypoint (`optcg` command)
tests/                  # Unit tests (pytest)
terraform/              # GCP infrastructure
public/css/             # Styled components — use these, don't invent new styles
```

## Running Tests

```bash
pytest tests/
```

Never test frontend behavior by starting a local server — write unit tests instead.

## CLI

```bash
optcg          # main CLI entrypoint
```

## Code Rules

- **Green coding:** Optimize for CPU, memory, and I/O. Prefer efficient data structures, batch/cache network calls, avoid polling.
- **HTMX-first:** Use HTMX for data-intensive interactive views before adding custom JavaScript.
- **Styling:** Use existing styled components from `/public/css`. Select components need an `id` for JS to work.
- **Mobile-first:** Design new frontend components for mobile first.
- **Frontend design skill:** When building new frontend components, pages, or UI sections, use the `frontend-design` skill (`/frontend-design`) to ensure production-grade, visually distinctive output.
- **No final reports:** Do not write a markdown summary at the end of a task.
- **No re-reads:** Do not read a file you have already read in the same session.
- **Refactor check:** When adding new code, check if nearby existing code should be refactored for consistency.
