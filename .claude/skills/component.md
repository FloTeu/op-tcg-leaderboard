---
description: Scaffold a new FastHTML page or reusable component following project conventions
---

Create a new FastHTML component or page as described. Follow these steps:

1. **Determine placement:** Page handler → `op_tcg/frontend/pages/`, reusable UI → `op_tcg/frontend/components/`, HTMX endpoint → `op_tcg/frontend/api/routes/`
2. **Read one closely related existing file** in the target directory before writing, so naming, imports, and structure are consistent.
3. **Data loading:** Fetch data via existing utils in `op_tcg/frontend/utils/` (e.g. `leader_data.py`, `cache.py`). Don't duplicate query logic.
4. **Interactivity:** Use HTMX attributes (`hx-get`, `hx-post`, `hx-target`, `hx-swap`) for dynamic parts. Add the corresponding route in `op_tcg/frontend/api/routes/` if needed.
5. **Styling:** Use existing CSS classes from `/public/css`. Mobile-first layout. Styled select elements must have an `id`.
6. **No custom JS** unless HTMX cannot cover the use case.
7. **Register the page** in the app's route list if it's a new page (check `op_tcg/frontend/api/routes/main.py` or similar entrypoint).
8. **Write a unit test** in `tests/` covering the main logic — no local server.