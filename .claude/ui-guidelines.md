# UI/UX Design Guidelines

Use the deck builder (`op_tcg/frontend/pages/deckbuilder.py`) as the canonical style reference for all new frontend work. The existing pages (home, leader, meta, card_movement, etc.) use raw Tailwind gray/blue with system fonts — do NOT extend that style. New work uses the guidelines below; old pages get migrated when touched significantly.

**Do not mix the old `bg-gray-800 text-white` Tailwind palette with the new one.**

## Styling Approach

**Prefer Tailwind utility classes over inline `style=` attributes** for all layout and spacing concerns (padding, margin, gap, flex, grid, sizing, etc.). Only use inline styles or custom CSS classes when the value is not expressible in standard Tailwind — primarily the design-token colors above (`#0d1424`, `#1a2540`, etc.) and custom animations.

```python
# Correct — Tailwind for layout/spacing
cls="flex items-center gap-4 p-5 px-4 mb-6 w-full grid grid-cols-3"

# Correct — inline style only for non-Tailwind design tokens
style="background:#0d1424; border:1px solid #1a2540; color:#f59e0b;"

# Avoid — inline style for things Tailwind handles
style="padding:20px 16px; display:flex; gap:16px;"
```

---

## Color Palette

```
Background page:    #070b14   (deepest navy — page wrapper / body)
Background panel:   #0d1424   (panel fill)
Background input:   #080e1c   (inputs, selects, code blocks)
Border default:     #1a2540
Border hover:       #2d3f5a
Text primary:       #f1f5f9
Text secondary:     #94a3b8
Text muted:         #475569   (also used for dim labels/section headers)
Text very dim:      #1e2d45   (placeholders, decorative only)
Accent gold:        #f59e0b   (primary interactive — active states, save, leader elements)
Accent gold hover:  #fbbf24
Accent gold glow:   rgba(245,158,11,0.12–0.35)
Accent cyan:        #38bdf8   (secondary interactive — search, filters, progress)
Accent cyan glow:   rgba(56,189,248,0.10–0.30)
Success:            #10b981
Error:              #ef4444
```

## Typography

Always import from Google Fonts:
```css
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
```

- **Bebas Neue** — headings, labels, section titles, button text, stat displays. `letter-spacing: 0.06–0.15em`
- **Barlow** — body text, descriptions, inputs, tooltips. Weight 400–600.
- **Share Tech Mono** — numbers, card IDs, counts, timestamps, codes, stats.

Never use Inter, Arial, Roboto, system-ui, or Tailwind's default font stack.

## Panels

```css
background: #0d1424;
border: 1px solid #1a2540;
border-radius: 12px;
```

`border-radius`: 8–12px panels · 6–8px sub-components · 4–6px chips/badges.

## Buttons

Primary (CTA):
```css
background: #f59e0b; color: #000; font-family: 'Bebas Neue'; letter-spacing: 0.1em;
border-radius: 8px; border: none; transition: background 0.12s, transform 0.1s;
```
Hover: `background: #fbbf24; transform: translateY(-1px)`

Ghost (secondary):
```css
background: transparent; color: #475569; border: 1px solid #1a2540;
font-family: 'Barlow'; border-radius: 6px;
```
Hover: `color: #94a3b8; border-color: #2d3f5a; background: #0d1424`

## Filter Chips / Tabs

```
Default: background #0d1424 · border #1a2540 · color #475569 · border-radius 20px
Active (gold): background rgba(245,158,11,0.12) · color #f59e0b · border rgba(245,158,11,0.35)
Active (cyan): background rgba(56,189,248,0.10) · color #38bdf8 · border rgba(56,189,248,0.30)
```

## Inputs & Selects

```css
background: #080e1c; color: #f1f5f9; border: 1px solid #1a2540;
border-radius: 8px; font-family: 'Barlow'; outline: none;
transition: border-color 0.15s, box-shadow 0.15s;
```
Focus: `border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08)`
Placeholder: `color: #1e2d45`

## Scrollbars

```css
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }
```

## Animations & Motion

- Hover transitions: `0.12–0.20s ease`
- Card hover lift: `transform: translateY(-4–5px) scale(1.02–1.06)` with `cubic-bezier(0.34, 1.56, 0.64, 1)` (spring)
- Press: `transform: scale(0.95–0.97); transition-duration: 0.06s`
- Entrances: `opacity 0→1` + `translateY(3–5px)→0`, stagger children with `animation-delay`
- One well-timed entrance > many scattered micro-animations

## Overlays / Modals

- Slide up: `transform: translateY(100%)→translateY(0)` with `cubic-bezier(0.22, 1, 0.36, 1)`
- Backdrop: blurred hero image `filter: blur(24px) brightness(0.15)`
- Header/footer: `backdrop-filter: blur(16–18px)` + `background: rgba(3,5,8,0.75)`
- Open sweep: horizontal cyan→gold gradient line animating `top: -3px → 100%`

## Layout

- Page wrapper: use `bg-deep-navy` Tailwind utility (defined globally in `main.py`, maps to `#070b14`). Also set `font-family: 'Barlow', sans-serif` via a page-scoped CSS class (e.g. `.wl-page`, `.db-page`) — do NOT inline the background color directly.
- Mobile-first. Stack vertically on mobile, side-by-side at `xl` (1280px+)
- Spacing via CSS Grid/Flexbox `gap`, not margin stacking
- Sticky sidebars: `position: sticky; top: 16px; max-height: calc(100vh - Npx); overflow-y: auto`

## HTMX / Loading States

**Standard component (use this by default):** `create_loading_spinner` from `op_tcg/frontend/components/loading.py`. Drop-in, centered, HTMX-indicator-ready. Use `create_loading_overlay` for absolute-positioned overlays. Both are the approved pattern for all pages.

```python
from op_tcg.frontend.components.loading import create_loading_spinner, create_loading_overlay

create_loading_spinner(id="my-indicator")          # inline centered spinner
create_loading_overlay(id="my-indicator")          # absolute overlay over a relative parent
```

**Custom inline spinner** (only for components that can't import Python, e.g. inline CSS in a `_styles()` block):
- Style: `border: 2–3px solid #1a2540; border-top-color: #38bdf8; border-radius: 50%; animation: rotate 0.65s linear infinite; box-shadow: 0 0 16px rgba(56,189,248,0.2)`
- Center over target: `position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%)` on a `position: relative` wrapper

**Both cases:** visibility via `opacity: 0→1` on `.htmx-indicator` — never `display: none`.