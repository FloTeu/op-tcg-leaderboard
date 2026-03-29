---
description: Review the current changes or specified file for code quality, green coding, and project conventions
---

Review the code changes (or the file/code I specify) against these criteria. Be concise — list issues only, no praise.

**Green coding**
- Unnecessary CPU cycles, inefficient algorithms, or missing caching opportunities
- Redundant I/O: repeated BQ queries, missing batching, un-cached network calls
- Memory leaks or oversized data structures

**FastHTML / HTMX**
- Data-intensive views that should use HTMX endpoints instead of full-page renders
- Custom JavaScript where an HTMX attribute would suffice
- Missing `id` on styled select components

**Styling & UX**
- Using ad-hoc styles instead of existing `/public/css` components
- Non-mobile-friendly layout decisions

**Code quality**
- Logic that could reuse existing utilities in `op_tcg/frontend/utils/` or `op_tcg/backend/utils/`
- Nearby code that should be refactored for consistency with the new addition
- Anything that would break unit tests (never test by starting a local server)

Output format: grouped bullet list by category. Skip categories with no issues.