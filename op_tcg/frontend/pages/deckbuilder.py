import json
import math
from fasthtml import ft
from fasthtml.common import NotStr
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup, get_all_tournament_decklist_data
from op_tcg.backend.models.cards import OPTcgCardCatagory
from op_tcg.backend.db import get_custom_decklists, get_decklist_watchlist

_CIRC = round(2 * math.pi * 36, 2)

_COLOR_DEFS = [
    ("Red",    "red",    "#ef4444", "Red"),
    ("Green",  "green",  "#22c55e", "Green"),
    ("Blue",   "blue",   "#3b82f6", "Blue"),
    ("Purple", "purple", "#a855f7", "Purple"),
    ("Black",  "black",  "#9ca3af", "Black"),
    ("Yellow", "yellow", "#eab308", "Yellow"),
]


def _styles() -> ft.Style:
    return ft.Style("""
.db-display { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.06em; }
.db-mono    { font-family: 'Share Tech Mono', monospace; }
.db-body    { font-family: 'Barlow', sans-serif; }

.db-page { font-family: 'Barlow', sans-serif; }

.db-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
}

.db-panel-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.db-leader-frame {
    background: #080e1c;
    border: 1.5px solid #1a2540;
    border-radius: 8px;
    min-height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 0.3s, box-shadow 0.3s;
    padding: 10px;
}
.db-leader-frame.has-leader {
    border-color: rgba(245,158,11,0.6);
    box-shadow: 0 0 24px rgba(245,158,11,0.12);
}

.db-filter-chip {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 500;
    background: #0d1424;
    color: #475569;
    border: 1px solid #1a2540;
    cursor: pointer;
    transition: all 0.12s;
    user-select: none;
    white-space: nowrap;
}
.db-filter-chip:hover { border-color: #2d3f5a; color: #64748b; }
.db-filter-chip.active {
    background: rgba(245,158,11,0.12);
    color: #f59e0b;
    border-color: rgba(245,158,11,0.35);
}
.db-chip-cat.active {
    background: rgba(56,189,248,0.1);
    color: #38bdf8;
    border-color: rgba(56,189,248,0.3);
}
.db-chip-color-red.active    { background:rgba(239,68,68,.12); color:#ef4444; border-color:rgba(239,68,68,.35); }
.db-chip-color-green.active  { background:rgba(34,197,94,.12); color:#22c55e; border-color:rgba(34,197,94,.35); }
.db-chip-color-blue.active   { background:rgba(59,130,246,.12); color:#60a5fa; border-color:rgba(59,130,246,.35); }
.db-chip-color-purple.active { background:rgba(168,85,247,.12); color:#c084fc; border-color:rgba(168,85,247,.35); }
.db-chip-color-black.active  { background:rgba(148,163,184,.12); color:#cbd5e1; border-color:rgba(148,163,184,.35); }
.db-chip-color-yellow.active { background:rgba(234,179,8,.12); color:#facc15; border-color:rgba(234,179,8,.35); }

.db-search {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.db-search:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }
.db-search::placeholder { color: #1e2d45; }

.db-leader-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 10px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.8rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s;
}
.db-leader-select:focus { border-color: #f59e0b; }

.db-name-input {
    background: transparent;
    border: none;
    border-bottom: 1.5px solid #1a2540;
    color: #f1f5f9;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 0.05em;
    padding: 2px 0 4px;
    outline: none;
    width: 100%;
    transition: border-color 0.15s;
    min-width: 0;
}
.db-name-input:focus { border-bottom-color: #f59e0b; }
.db-name-input::placeholder { color: #1a2540; }

.db-btn-primary {
    background: #f59e0b;
    color: #000;
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 1rem;
    padding: 7px 22px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: background 0.12s, transform 0.1s;
    white-space: nowrap;
}
.db-btn-primary:hover { background: #fbbf24; transform: translateY(-1px); }
.db-btn-primary:disabled { background: #1a2540; color: #334155; transform: none; cursor: not-allowed; }

.db-btn-ghost {
    background: transparent;
    color: #475569;
    font-family: 'Barlow', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #1a2540;
    cursor: pointer;
    transition: all 0.12s;
    white-space: nowrap;
}
.db-btn-ghost:hover { color: #94a3b8; border-color: #2d3f5a; background: #0d1424; }

.db-deck-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 5px;
}

.db-deck-card {
    position: relative;
    cursor: pointer;
    border-radius: 5px;
    overflow: hidden;
    border: 1.5px solid #1a2540;
    user-select: none;
    -webkit-user-select: none;
    transition: transform 0.18s cubic-bezier(0.34,1.56,0.64,1),
                border-color 0.15s ease,
                box-shadow 0.15s ease;
}
.db-deck-card:hover {
    transform: scale(1.06);
    border-color: rgba(239,68,68,0.5);
    box-shadow: 0 6px 18px rgba(0,0,0,0.5), 0 0 0 1px rgba(239,68,68,0.2);
}
.db-deck-card:active { transform: scale(0.95); transition-duration: 0.06s; }

.db-deck-card-count {
    position: absolute;
    top: 3px; right: 3px;
    min-width: 16px; height: 16px;
    padding: 0 3px;
    border-radius: 8px;
    background: rgba(7,11,20,0.88);
    border: 1.5px solid rgba(245,158,11,0.6);
    color: #fcd34d;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.5rem;
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    pointer-events: none;
    z-index: 10;
    line-height: 1;
}

.db-deck-card-strip {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 14px 4px 4px;
    background: linear-gradient(transparent, rgba(4,7,16,0.96) 45%);
    opacity: 0;
    transition: opacity 0.15s ease;
    pointer-events: none;
}
.db-deck-card:hover .db-deck-card-strip { opacity: 1; }

.db-deck-card::after {
    content: '';
    position: absolute; inset: 0;
    background: rgba(239,68,68,0);
    transition: background 0.15s ease;
    pointer-events: none;
    border-radius: inherit;
}
.db-deck-card:hover::after { background: rgba(239,68,68,0.1); }

.db-progress-ring { transition: stroke-dashoffset 0.4s cubic-bezier(.4,0,.2,1), stroke 0.3s; }

.db-cost-bar-wrap {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 52px;
}
.db-cost-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-end;
    cursor: pointer;
    gap: 2px;
}
.db-cost-bar {
    background: rgba(245,158,11,0.45);
    border-radius: 2px 2px 0 0;
    min-height: 2px;
    transition: height 0.25s ease, background 0.15s ease;
}
.db-cost-col:hover .db-cost-bar { background: rgba(245,158,11,0.75); }
.db-cost-col.active .db-cost-bar {
    background: rgba(56,189,248,0.75);
    box-shadow: 0 0 8px rgba(56,189,248,0.3);
}
.db-cost-label {
    text-align: center;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.52rem;
    color: #1e2d45;
    line-height: 1;
    transition: color 0.15s;
    user-select: none;
}
.db-cost-col:hover .db-cost-label { color: #475569; }
.db-cost-col.active .db-cost-label { color: #38bdf8; }

.db-tab-btn {
    flex: 1; padding: 10px 4px;
    background: transparent; border: none;
    color: #334155;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem; letter-spacing: 0.1em;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.12s;
}
.db-tab-btn.active-tab { color: #f59e0b; border-bottom-color: #f59e0b; }

.db-card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
@media (min-width: 640px) { .db-card-grid { grid-template-columns: repeat(4, 1fr); } }
@media (min-width: 1024px) { .db-card-grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 1280px) { .db-card-grid { grid-template-columns: repeat(4, 1fr); } }

.db-two-col { display: flex; flex-direction: column; gap: 1rem; }
@media (min-width: 1280px) {
    .db-two-col { display: grid; grid-template-columns: 1fr 420px; gap: 1rem; align-items: start; }
    .db-xl-show { display: block !important; }
}

.db-card-item {
    position: relative;
    background: #070b14;
    border: 1.5px solid #1a2540;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    user-select: none;
    -webkit-user-select: none;
    transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1),
                border-color 0.15s ease,
                box-shadow 0.15s ease;
}
.db-card-item:hover {
    transform: translateY(-5px) scale(1.03);
    border-color: rgba(56,189,248,0.55);
    box-shadow: 0 14px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(56,189,248,0.2), inset 0 0 24px rgba(56,189,248,0.04);
}
.db-card-item.is-leader:hover {
    border-color: rgba(245,158,11,0.55);
    box-shadow: 0 14px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(245,158,11,0.2), inset 0 0 24px rgba(245,158,11,0.04);
}
.db-card-item:active { transform: translateY(-1px) scale(0.97); transition-duration: 0.06s; }
.db-card-item.is-maxed {
    opacity: 0.28;
    cursor: not-allowed;
    pointer-events: none;
    filter: saturate(0.2);
}

/* Count badge */
.db-card-count {
    position: absolute;
    top: 5px; right: 5px;
    min-width: 20px; height: 20px;
    padding: 0 4px;
    border-radius: 10px;
    background: rgba(7,11,20,0.85);
    border: 1.5px solid rgba(56,189,248,0.55);
    color: #7dd3fc;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.6rem;
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    opacity: 0;
    transform: scale(0.4) rotate(12deg);
    transition: opacity 0.2s ease, transform 0.28s cubic-bezier(0.34,1.56,0.64,1);
    pointer-events: none;
    line-height: 1;
    z-index: 10;
}
.db-card-count.visible { opacity: 1; transform: scale(1) rotate(0deg); }
.db-card-item.is-leader .db-card-count {
    border-color: rgba(245,158,11,0.55);
    color: #fcd34d;
}

/* Info strip on hover */
.db-card-info-strip {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 18px 7px 6px;
    background: linear-gradient(to bottom, transparent, rgba(4,7,16,0.96) 45%);
    opacity: 0;
    transform: translateY(4px);
    transition: opacity 0.2s ease, transform 0.2s ease;
    pointer-events: none;
}
.db-card-item:hover .db-card-info-strip { opacity: 1; transform: translateY(0); }
.db-card-name-strip {
    display: block;
    font-family: 'Barlow', sans-serif;
    font-size: 0.62rem; font-weight: 600;
    color: #e2e8f0; line-height: 1.25;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.db-card-cost-strip {
    display: block;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.52rem; color: #475569;
    margin-top: 1px;
}

/* Leader crown badge */
.db-card-leader-crown {
    position: absolute; top: 5px; left: 6px;
    font-size: 0.65rem;
    color: rgba(245,158,11,0.75);
    text-shadow: 0 0 10px rgba(245,158,11,0.4);
    pointer-events: none;
    z-index: 10;
    line-height: 1;
}

/* Click flash animations */
@keyframes db-flash-blue {
    0%   { background: rgba(56,189,248,0); }
    20%  { background: rgba(56,189,248,0.28); }
    100% { background: rgba(56,189,248,0); }
}
@keyframes db-flash-gold {
    0%   { background: rgba(245,158,11,0); }
    20%  { background: rgba(245,158,11,0.28); }
    100% { background: rgba(245,158,11,0); }
}
.db-card-flash-blue::after  { content:''; position:absolute; inset:0; animation: db-flash-blue 0.38s ease-out; pointer-events:none; border-radius:inherit; }
.db-card-flash-gold::after  { content:''; position:absolute; inset:0; animation: db-flash-gold 0.38s ease-out; pointer-events:none; border-radius:inherit; }

/* Search loading indicator */
.htmx-indicator { opacity: 0; transition: opacity 150ms ease; pointer-events: none; }
.htmx-request .htmx-indicator { opacity: 1; }
.htmx-request.htmx-indicator { opacity: 1; }

.db-spin {
    width: 32px; height: 32px;
    border: 3px solid #1a2540;
    border-top-color: #38bdf8;
    border-radius: 50%;
    flex-shrink: 0;
    animation: db-rotate 0.65s linear infinite;
    box-shadow: 0 0 16px rgba(56,189,248,0.2);
}
@keyframes db-rotate { to { transform: rotate(360deg); } }

.db-scroll::-webkit-scrollbar { width: 3px; }
.db-scroll::-webkit-scrollbar-track { background: transparent; }
.db-scroll::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }

@keyframes dbFadeIn { from { opacity:0; transform:scale(.96) translateY(3px); } to { opacity:1; transform:none; } }
#cdb-search-results .db-card-item { animation: dbFadeIn 0.18s ease; }

/* Leader hero */
.db-leader-hero {
    position: relative;
    height: 160px;
    overflow: hidden;
    border-radius: 8px 8px 0 0;
    margin: -16px -16px 12px;
    background: #030508;
}
.db-leader-hero-bg {
    position: absolute; inset: 0;
    background-size: cover;
    background-position: center 15%;
    transition: background-image 0.35s ease;
    filter: brightness(0.75) saturate(1.1);
}
.db-leader-hero-overlay {
    position: absolute; inset: 0;
    background: linear-gradient(160deg, transparent 30%, rgba(7,11,20,0.92) 90%);
    display: flex; align-items: flex-end;
    padding: 10px 12px;
}
.db-leader-hero-name {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em;
    font-size: 1.15rem;
    color: #f1f5f9;
    line-height: 1;
    text-shadow: 0 1px 8px rgba(0,0,0,0.8);
}
.db-leader-hero.has-leader .db-leader-hero-name { color: #fef3c7; }

/* Compact filter row */
.db-filter-divider {
    width: 1px; height: 18px;
    background: #1a2540;
    flex-shrink: 0;
    align-self: center;
    margin: 0 4px;
}

/* Counter chips */
.db-counter-chips { display: flex; gap: 6px; }
.db-counter-chip {
    flex: 1;
    display: flex; flex-direction: column; align-items: center;
    padding: 6px 4px 5px;
    border-radius: 7px;
    background: #080e1c;
    border: 1.5px solid #1a2540;
    cursor: pointer;
    transition: border-color 0.14s, background 0.14s;
    min-width: 0;
}
.db-counter-chip:hover { border-color: #2d3f5a; background: #0d1424; }
.db-counter-chip.active {
    border-color: rgba(56,189,248,0.5);
    background: rgba(56,189,248,0.07);
    box-shadow: 0 0 12px rgba(56,189,248,0.08);
}
.db-counter-chip-val {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1;
    margin-bottom: 3px;
}
.db-counter-chip.active .db-counter-chip-val { color: #7dd3fc; }
.db-counter-chip-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em;
    font-size: 0.52rem;
    color: #334155;
    line-height: 1;
}
.db-counter-chip.active .db-counter-chip-label { color: #38bdf8; }

/* Sticky panels on desktop */
@media (min-width: 1280px) {
    .db-panel-sticky { position: sticky; top: 16px; max-height: calc(100vh - 120px); overflow-y: auto; }
    .db-panel-sticky.db-scroll::-webkit-scrollbar { width: 3px; }
}

/* ── Fullscreen deck overlay ─────────────────────────────────────── */
.db-fs-overlay {
    position: fixed; inset: 0; z-index: 9000;
    display: flex; flex-direction: column;
    transform: translateY(100%);
    transition: transform 0.44s cubic-bezier(0.22, 1, 0.36, 1);
    overflow: hidden;
    background: #030508;
}
.db-fs-overlay.open { transform: translateY(0); }

.db-fs-bg {
    position: absolute; inset: 0;
    background-size: cover; background-position: center 20%;
    filter: blur(28px) brightness(0.14) saturate(1.5);
    transform: scale(1.1);
    z-index: 0;
    transition: background-image 0.4s ease;
}
.db-fs-vignette {
    position: absolute; inset: 0; z-index: 1; pointer-events: none;
    background: radial-gradient(ellipse 130% 110% at 50% 0%, transparent 30%, rgba(3,5,8,0.92) 90%);
}
@keyframes db-fs-sweep {
    from { top: -3px; opacity: 1; }
    to   { top: 100%; opacity: 0; }
}
.db-fs-sweep {
    position: absolute; left: 0; right: 0; height: 2px; z-index: 4; pointer-events: none;
    background: linear-gradient(90deg, transparent, rgba(56,189,248,0.8) 40%, rgba(245,158,11,0.6) 60%, transparent);
    animation: db-fs-sweep 0.75s ease-out forwards;
}

.db-fs-header {
    position: relative; z-index: 10; flex-shrink: 0;
    display: flex; align-items: center; gap: 14px;
    padding: 13px 20px 11px;
    background: rgba(3,5,8,0.78);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(245,158,11,0.12);
}
.db-fs-leader-name {
    font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.1em;
    font-size: clamp(1rem, 2.5vw, 1.5rem);
    color: #fef3c7; line-height: 1;
    text-shadow: 0 0 40px rgba(245,158,11,0.3);
    flex-shrink: 0;
}
.db-fs-total {
    font-family: 'Share Tech Mono', monospace; font-size: 0.8rem;
    flex-shrink: 0; white-space: nowrap;
}
.db-fs-mini-curve {
    display: flex; align-items: flex-end; gap: 2px; height: 22px; flex-shrink: 0;
}
.db-fs-mini-bar {
    width: 7px; min-height: 2px;
    background: rgba(245,158,11,0.4);
    border-radius: 1px 1px 0 0;
    transition: height 0.25s ease;
}
.db-fs-close {
    margin-left: auto; width: 34px; height: 34px; border-radius: 50%;
    background: rgba(20,30,50,0.6); border: 1px solid #1a2540;
    color: #475569; font-size: 0.9rem; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s; flex-shrink: 0;
}
.db-fs-close:hover { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4); color: #ef4444; }

.db-fs-body {
    position: relative; z-index: 5; flex: 1; overflow-y: auto;
    padding: 16px 20px 20px;
}
.db-fs-section { margin-bottom: 20px; }
.db-fs-section-hdr {
    display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
    font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.15em; font-size: 0.6rem;
    color: rgba(245,158,11,0.45);
}
.db-fs-section-hdr::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(245,158,11,0.12), transparent);
}
.db-fs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(78px, 1fr));
    gap: 8px;
}
@media (min-width: 480px) { .db-fs-grid { grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); } }
@media (min-width: 1024px) { .db-fs-grid { grid-template-columns: repeat(auto-fill, minmax(108px, 1fr)); } }

.db-fs-card {
    position: relative; border-radius: 6px; overflow: hidden;
    border: 1.5px solid #1a2540; cursor: pointer;
    user-select: none; -webkit-user-select: none;
    transition: transform 0.18s cubic-bezier(0.34,1.56,0.64,1), border-color 0.15s, box-shadow 0.15s;
    aspect-ratio: 421 / 600;
}
.db-fs-card:hover {
    transform: scale(1.06) translateY(-4px);
    border-color: rgba(239,68,68,0.5);
    box-shadow: 0 14px 30px rgba(0,0,0,0.65), 0 0 0 1px rgba(239,68,68,0.15);
    z-index: 2;
}
.db-fs-card:active { transform: scale(0.95); transition-duration: 0.06s; }
.db-fs-card img { width: 100%; height: 100%; object-fit: cover; display: block; }
.db-fs-card-cnt {
    position: absolute; top: 4px; right: 4px;
    min-width: 18px; height: 18px; padding: 0 3px; border-radius: 9px;
    background: rgba(7,11,20,0.88); border: 1.5px solid rgba(245,158,11,0.6);
    color: #fcd34d; font-family: 'Share Tech Mono', monospace; font-size: 0.55rem;
    display: flex; align-items: center; justify-content: center;
    pointer-events: none; z-index: 10; backdrop-filter: blur(4px);
}
.db-fs-card-strip {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 16px 5px 5px;
    background: linear-gradient(transparent, rgba(4,7,16,0.95) 50%);
    opacity: 0; transition: opacity 0.15s; pointer-events: none;
}
.db-fs-card:hover .db-fs-card-strip { opacity: 1; }
.db-fs-card-strip span {
    display: block; font-family: 'Barlow', sans-serif;
    font-size: 0.6rem; font-weight: 600; color: #e2e8f0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.db-fs-footer {
    position: relative; z-index: 10; flex-shrink: 0;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 10px 20px;
    background: rgba(3,5,8,0.78);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-top: 1px solid rgba(26,37,64,0.8);
}
.db-fs-footer-type {
    display: flex; flex-direction: column; align-items: center;
    padding: 0 10px; border-left: 1px solid #1a2540; flex-shrink: 0;
}
.db-fs-footer-type-val {
    font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; color: #475569; line-height: 1;
}
.db-fs-footer-type-label {
    font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.08em;
    font-size: 0.5rem; color: #1e2d45; margin-top: 2px;
}

/* Expand button */
.db-expand-btn {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 8px; border-radius: 5px;
    background: transparent; border: 1px solid #1a2540;
    color: #334155; font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em; font-size: 0.62rem;
    cursor: pointer; transition: all 0.12s; white-space: nowrap;
}
.db-expand-btn:hover { border-color: #2d3f5a; color: #64748b; background: #080e1c; }

/* ── Starting Hand overlay ──────────────────────────────────────────── */
.db-hand-overlay {
    position: fixed; inset: 0; z-index: 9500;
    display: flex; align-items: center; justify-content: center;
    opacity: 0; pointer-events: none;
    transition: opacity 0.25s ease;
    background: rgba(3,5,8,0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}
.db-hand-overlay.open { opacity: 1; pointer-events: all; }

.db-hand-modal {
    display: flex; flex-direction: column; align-items: center;
    padding: 28px 24px 36px; width: 100%;
    transform: translateY(24px);
    transition: transform 0.3s cubic-bezier(0.22,1,0.36,1);
}
.db-hand-overlay.open .db-hand-modal { transform: translateY(0); }

.db-hand-header {
    position: relative;
    display: flex; align-items: center; justify-content: center;
    width: 100%; margin-bottom: 4px;
}
.db-hand-title-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.18em; font-size: 1.5rem;
    color: #fef3c7;
    text-shadow: 0 0 30px rgba(245,158,11,0.3);
}
.db-hand-subtitle {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.58rem; color: #334155;
    letter-spacing: 0.1em; margin-bottom: 8px;
}
.db-hand-close {
    position: absolute; right: 0; top: 50%; transform: translateY(-50%);
    width: 30px; height: 30px; border-radius: 50%;
    background: rgba(20,30,50,0.6); border: 1px solid #1a2540;
    color: #475569; font-size: 0.8rem; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
}
.db-hand-close:hover { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4); color: #ef4444; }

.db-hand-cards {
    display: flex; align-items: flex-end; justify-content: center;
    padding: 12px 0 8px;
}
.db-hand-card-outer {
    flex-shrink: 0;
    margin: 0 -10px;
    position: relative;
    transform-origin: center bottom;
}
.db-hand-card-outer:hover { z-index: 10; }
.db-hand-card-outer:hover .db-hand-card-inner {
    transform: translateY(-22px) scale(1.07);
    border-color: rgba(245,158,11,0.55);
    box-shadow: 0 22px 44px rgba(0,0,0,0.75), 0 0 22px rgba(245,158,11,0.18);
}
.db-hand-card-inner {
    width: 88px;
    border-radius: 7px; overflow: hidden;
    border: 1.5px solid #1a2540;
    box-shadow: 0 6px 20px rgba(0,0,0,0.65);
    transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), border-color 0.15s, box-shadow 0.15s;
    animation: db-deal-in 0.42s cubic-bezier(0.34,1.56,0.64,1) both;
}
@media (min-width: 480px) { .db-hand-card-inner { width: 108px; } }
@media (min-width: 768px) { .db-hand-card-inner { width: 130px; } }

@keyframes db-deal-in {
    from { opacity: 0; transform: translateY(48px) scale(0.82); }
    to   { opacity: 1; }
}

.db-hand-actions { display: flex; gap: 10px; margin-top: 20px; }
.db-hand-btn-draw {
    background: rgba(245,158,11,0.12);
    color: #f59e0b; border: 1px solid rgba(245,158,11,0.35);
    font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.12em;
    font-size: 0.92rem; padding: 8px 26px; border-radius: 8px;
    cursor: pointer;
    transition: background 0.12s, border-color 0.12s, transform 0.1s;
}
.db-hand-btn-draw:hover {
    background: rgba(245,158,11,0.22);
    border-color: rgba(245,158,11,0.55);
    transform: translateY(-1px);
}
""")


def _page_script(prefill_data: dict) -> ft.Script:
    # Tiny init script — all logic lives in public/js/deckbuilder.js
    init_json = json.dumps(prefill_data)
    return ft.Script(f"""
window._cdbInit = {init_json};
if (typeof window._dbSetup === 'function') {{
  window._dbSetup();
}} else {{
  document.addEventListener('DOMContentLoaded', function() {{
    if (typeof window._dbSetup === 'function') window._dbSetup();
  }});
}}
""")


def deckbuilder_page(request):
    user = request.session.get('user')
    if not user:
        return ft.Div(
            ft.H1("Access Denied", cls="db-display text-3xl text-white mb-4"),
            ft.P("Please log in to use the Deck Builder.", cls="text-gray-400 db-body"),
            ft.A("Log in", href="/login", cls="inline-block mt-4 db-btn-primary"),
            cls="db-page bg-deep-navy db-body min-h-screen flex flex-col items-center justify-center gap-2"
        )

    user_id = user.get('sub')
    card_lookup = get_card_id_card_data_lookup()
    custom_id = request.query_params.get('custom_id', '')
    import_tournament_id = request.query_params.get('import_tournament_id', '')
    import_player_id = request.query_params.get('import_player_id', '')
    import_custom_id = request.query_params.get('import_custom_id', '')

    # Resolve prefill (edit mode or import)
    prefill_name, prefill_leader_id, prefill_leader_img, prefill_leader_name, prefill_decklist = '', '', '', '', {}
    if custom_id:
        customs = get_custom_decklists(user_id)
        match = next((d for d in customs if d.get('id') == custom_id), None)
        if match:
            prefill_name = match.get('name', '')
            prefill_leader_id = match.get('leader_id', '')
            prefill_decklist = {k: int(v) for k, v in (match.get('decklist') or {}).items()}

    if import_tournament_id and import_player_id:
        td = next(
            (x for x in get_all_tournament_decklist_data()
             if x.tournament_id == import_tournament_id and x.player_id == import_player_id),
            None,
        )
        if td:
            prefill_decklist = {k: int(v) for k, v in (td.decklist or {}).items()}
            prefill_leader_id = td.leader_id  # always override — import brings its own leader

    if import_custom_id:
        for d in get_custom_decklists(user_id):
            if d.get('id') == import_custom_id:
                prefill_decklist = {k: int(v) for k, v in (d.get('decklist') or {}).items()}
                prefill_leader_id = d.get('leader_id', '')  # always override
                break

    if prefill_leader_id in card_lookup:
        lc = card_lookup[prefill_leader_id]
        prefill_leader_img = lc.image_url
        prefill_leader_name = lc.name

    # Build prefill_cards for JS
    prefill_cards = {}
    for cid, count in prefill_decklist.items():
        c = card_lookup.get(cid)
        prefill_cards[cid] = {
            'count': int(count),
            'name': c.name if c else cid,
            'img': c.image_url if c else '',
            'is_leader': (c.card_category == OPTcgCardCatagory.LEADER) if c else False,
            'cost': int(c.cost or 0) if c and c.cost else 0,
            'type': c.card_category.value if c else '',
            'counter': int(c.counter) if c and c.counter else 0,
            'has_trigger': ('[Trigger]' in c.ability) if c else False,
        }

    # Ensure leader card is always present in prefill_cards
    if prefill_leader_id and prefill_leader_id not in prefill_cards:
        lc = card_lookup.get(prefill_leader_id)
        if lc:
            prefill_cards[prefill_leader_id] = {
                'count': 1,
                'name': lc.name,
                'img': lc.image_url,
                'is_leader': True,
                'cost': 0,
                'type': lc.card_category.value,
                'counter': 0,
            }

    prefill_leader_colors = []
    if prefill_leader_id in card_lookup:
        prefill_leader_colors = [col.value for col in card_lookup[prefill_leader_id].colors]

    prefill_data = {
        'cards': prefill_cards,
        'leaderId': prefill_leader_id,
        'leaderName': prefill_leader_name,
        'leaderImg': prefill_leader_img,
        'leaderColors': prefill_leader_colors,
        'customId': custom_id or None,
    }

    # Leader dropdown options
    leaders_sorted = sorted(
        [c for c in card_lookup.values() if c.card_category == OPTcgCardCatagory.LEADER],
        key=lambda c: (c.meta_format or '', c.name), reverse=True,
    )
    leader_opts = [ft.Option("— select leader —", value="", disabled=True, selected=not prefill_leader_id)]
    for lc in leaders_sorted:
        leader_opts.append(ft.Option(
            f"{lc.name} ({lc.id})",
            value=lc.id,
            selected=(lc.id == prefill_leader_id),
            data_leader_name=lc.name,
            data_leader_img=lc.image_url,
            data_leader_colors=json.dumps([c.value for c in lc.colors]),
        ))

    # Import options
    dl_watchlist = get_decklist_watchlist(user_id)
    customs_all = get_custom_decklists(user_id)
    import_opts = [ft.Option("— import from —", value="", disabled=True, selected=True)]
    if dl_watchlist:
        import_opts.append(ft.Option("── Tournament Decklists ──", value="", disabled=True))
        for item in dl_watchlist:
            lid = item.get('leader_id', '')
            lname = card_lookup[lid].name if lid in card_lookup else lid
            tid = item.get('tournament_id', '')
            pid = item.get('player_id', '')
            url = f"/deckbuilder?import_tournament_id={tid}&import_player_id={pid}" + (f"&custom_id={custom_id}" if custom_id else "")
            import_opts.append(ft.Option(f"{lname} — {tid[:28]}", value=f"t:{tid}:{pid}", data_import_url=url))
    if customs_all:
        import_opts.append(ft.Option("── Custom Decklists ──", value="", disabled=True))
        for d in customs_all:
            if d.get('id') == custom_id:
                continue
            url = f"/deckbuilder?import_custom_id={d['id']}" + (f"&custom_id={custom_id}" if custom_id else "")
            import_opts.append(ft.Option(d.get('name', 'Unnamed'), value=f"c:{d['id']}", data_import_url=url))

    # ── Subcomponents ────────────────────────────────────────────────────────

    hx_include = "#cdb-search, #cdb-color-filters, #cdb-category-filters"

    # Search panel: filters + search input + results
    search_panel = ft.Div(
        # Compact filter row (colors + divider + types in one line)
        ft.Div(
            *[
                ft.Button(
                    ft.Span(cls="w-2 h-2 rounded-full flex-shrink-0 mr-1",
                            style=f"background:{hex_col}"),
                    label,
                    type="button",
                    cls=f"db-filter-chip db-chip-color db-chip-color-{key}",
                    data_color=val,
                    onclick="window._dbToggleColor(this)",
                )
                for label, key, hex_col, val in _COLOR_DEFS
            ],
            ft.Span(cls="db-filter-divider"),
            *[
                ft.Button(
                    cat.value,
                    type="button",
                    cls="db-filter-chip db-chip-cat",
                    data_cat=cat.value,
                    onclick="window._dbToggleCat(this)",
                )
                for cat in [OPTcgCardCatagory.CHARACTER, OPTcgCardCatagory.EVENT, OPTcgCardCatagory.STAGE]
            ],
            ft.Div(id="cdb-color-filters"),
            ft.Div(id="cdb-category-filters"),
            cls="flex flex-wrap items-center gap-1.5 mb-3",
        ),
        ft.Input(
            type="text", name="search_term", id="cdb-search",
            placeholder="Search by name, type, set… (e.g. OP09 Luffy)",
            cls="db-search mb-3",
            hx_get="/api/decklist-builder/card-search",
            hx_trigger="keyup changed delay:350ms, db-search",
            hx_target="#cdb-search-results",
            hx_swap="innerHTML",
            hx_include=hx_include,
            hx_indicator="#cdb-search-spinner",
        ),
        ft.Div(
            ft.Div(
                ft.P("Type to search for cards.", cls="text-center db-body",
                     style="color:#1e2d45;font-size:.8rem;padding:40px 0;"),
                id="cdb-search-results",
                cls="db-scroll overflow-y-auto",
                style="max-height:calc(100vh - 230px); min-height:120px;",
            ),
            ft.Div(
                ft.Div(cls="db-spin"),
                id="cdb-search-spinner",
                cls="htmx-indicator",
                style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); z-index:20;",
            ),
            style="position:relative; min-height:120px;",
        ),
        cls="db-panel p-4 flex flex-col",
        style="min-height: 400px;",
    )

    # Deck panel: leader hero + stats + deck grid + cost curve + import
    deck_panel = ft.Div(
        # ── Leader hero ──────────────────────────────────────────────────
        ft.Div(
            ft.Div(
                id="cdb-leader-hero-bg",
                cls="db-leader-hero-bg",
                style=f'background-image:url("{prefill_leader_img}");' if prefill_leader_img else "",
            ),
            ft.Div(
                ft.Span(
                    prefill_leader_name or "SELECT A LEADER",
                    id="cdb-leader-hero-name",
                    cls="db-leader-hero-name",
                ),
                cls="db-leader-hero-overlay",
            ),
            cls=f"db-leader-hero{'  has-leader' if prefill_leader_id else ''}",
            id="cdb-leader-hero",
        ),
        # ── Leader dropdown ──────────────────────────────────────────────
        ft.Select(
            *leader_opts,
            id="cdb-leader-select",
            cls="db-leader-select styled-select mb-4",
            onchange="window._cdbLeaderChange(this)",
        ),
        # ── Stats: ring + type counts ────────────────────────────────────
        ft.Div(
            ft.Div(
                NotStr(
                    f'<svg viewBox="0 0 80 80" style="width:56px;height:56px;">'
                    f'<circle cx="40" cy="40" r="36" fill="none" stroke="#111d30" stroke-width="5"/>'
                    f'<circle id="db-ring" cx="40" cy="40" r="36" fill="none"'
                    f' stroke="#f59e0b" stroke-width="5"'
                    f' stroke-dasharray="{_CIRC}" stroke-dashoffset="{_CIRC}"'
                    f' stroke-linecap="round"'
                    f' class="db-progress-ring"'
                    f' style="transform:rotate(-90deg);transform-origin:50% 50%;"/>'
                    f'</svg>'
                ),
                ft.Div(
                    ft.Span("0", id="db-ring-num",
                            style="font-family:'Share Tech Mono',monospace;font-size:1.1rem;color:#f1f5f9;line-height:1;"),
                    ft.Span("/50",
                            style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#334155;"),
                    style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;",
                ),
                style="position:relative;width:56px;height:56px;flex-shrink:0;",
            ),
            ft.Div(
                *[
                    ft.Div(
                        ft.Span(cat, cls="db-panel-label mb-0"),
                        ft.Span("0", id=f"db-tc-{cat.lower()}",
                                style="font-family:'Share Tech Mono',monospace;font-size:.85rem;color:#475569;"),
                        cls="flex flex-col items-center",
                    )
                    for cat in ["Character", "Event", "Stage"]
                ],
                cls="flex gap-3 items-center",
            ),
            cls="flex items-center gap-4 mb-4",
        ),
        # ── Counter analytics ────────────────────────────────────────────
        ft.Div(
            ft.Div("Counter", cls="db-panel-label"),
            ft.Div(
                *[
                    ft.Button(
                        ft.Span("0", id=f"db-cn-{key}", cls="db-counter-chip-val"),
                        ft.Span(label, cls="db-counter-chip-label"),
                        type="button",
                        cls="db-counter-chip",
                        id=f"db-counter-{key}",
                        onclick=f"window._dbToggleCounterFilter({val})",
                        title=title,
                    )
                    for key, label, val, title in [
                        ("none", "No Counter", "null", "No counter — click to filter"),
                        ("1k",   "+1000",      "1000", "+1000 counter — click to filter"),
                        ("2k",   "+2000",      "2000", "+2000 counter — click to filter"),
                    ]
                ],
                ft.Button(
                    ft.Span("0", id="db-cn-trigger", cls="db-counter-chip-val"),
                    ft.Span("Trigger", cls="db-counter-chip-label"),
                    type="button",
                    cls="db-counter-chip",
                    id="db-counter-trigger",
                    onclick="window._dbToggleTriggerFilter()",
                    title="Cards with Trigger — click to filter",
                ),
                cls="db-counter-chips",
            ),
            cls="mb-4",
        ),
        # ── Deck label + expand button ───────────────────────────────────
        ft.Div(
            ft.Span("MY DECK",
                    style="font-family:'Bebas Neue',sans-serif;letter-spacing:.12em;font-size:.6rem;color:#334155;"),
            ft.Div(
                ft.Button(
                    ft.I(cls="fas fa-random text-xs mr-1"),
                    "HAND",
                    type="button",
                    cls="db-expand-btn",
                    onclick="window._dbDrawHand()",
                ),
                ft.Button(
                    ft.I(cls="fas fa-expand-alt text-xs mr-1"),
                    "FULL VIEW",
                    type="button",
                    cls="db-expand-btn",
                    onclick="window._dbOpenFullscreen()",
                ),
                cls="flex items-center gap-1",
            ),
            cls="flex items-center justify-between mb-2",
        ),
        # ── Deck card grid ───────────────────────────────────────────────
        ft.Div(
            ft.P("Add cards from the browser",
                 style="color:#1e2d45;font-family:Barlow,sans-serif;font-size:.8rem;text-align:center;padding:24px 0;"),
            id="cdb-decklist-panel",
            cls="db-scroll overflow-y-auto mb-4",
            style="max-height: calc(100vh - 500px); min-height: 120px;",
        ),
        ft.Input(type="hidden", id="cdb-decklist-json", value="{}"),
        # ── Cost curve ───────────────────────────────────────────────────
        ft.Div(
            ft.Div("Cost Curve", cls="db-panel-label"),
            ft.Div(
                *[
                    ft.Div(
                        ft.Div(id=f"db-bar-{i}", cls="db-cost-bar", style="height:2px;"),
                        ft.Span(str(i) if i < 10 else "10+", cls="db-cost-label"),
                        id=f"db-cost-col-{i}",
                        cls="db-cost-col",
                        onclick=f"window._dbToggleCostFilter({i})",
                    )
                    for i in range(11)
                ],
                cls="db-cost-bar-wrap",
            ),
            cls="mb-4",
        ),
        # ── Import ───────────────────────────────────────────────────────
        ft.Div(
            ft.Div("Import", cls="db-panel-label"),
            ft.Div(
                ft.Select(
                    *import_opts,
                    id="cdb-import-select",
                    cls="db-leader-select",
                    style="flex:1;",
                    onchange="window._cdbImportChange(this)",
                ),
                ft.Button(
                    ft.I(cls="fas fa-clipboard text-xs"),
                    type="button",
                    cls="db-btn-ghost flex-shrink-0",
                    title="Paste from clipboard",
                    onclick="window._cdbPasteImport()",
                ),
                cls="flex gap-2 items-center",
            ),
        ),
        cls="db-panel db-panel-sticky db-scroll p-4",
    )

    # ── Page header ──────────────────────────────────────────────────────────
    page_header = ft.Div(
        ft.Div(
            ft.A("← Watchlist", href="/watchlist?section=decklists",
                 style="font-family:Barlow,sans-serif;font-size:.72rem;color:#334155;text-decoration:none;transition:color .15s;"
                        " onmouseover=\"this.style.color='#64748b'\" onmouseout=\"this.style.color='#334155'\""),
            ft.H1(
                "Edit Deck" if custom_id else "Deck Builder",
                cls="db-display",
                style="font-size:2rem;color:#f1f5f9;margin:2px 0 0;line-height:1;",
            ),
        ),
        ft.Div(
            ft.Input(
                id="cdb-name", type="text",
                value=prefill_name,
                placeholder="NAME YOUR DECK",
                cls="db-name-input",
                style="max-width:320px;",
            ),
        ),
        ft.Div(
            ft.Button(
                ft.I(cls="fas fa-file-export mr-1.5 text-xs"),
                "Export",
                id="db-export-btn",
                type="button",
                cls="db-btn-ghost",
                onclick="window._dbExport()",
            ),
            ft.Button(
                ft.I(cls="fas fa-save mr-1.5 text-xs"),
                "SAVE DECK",
                id="cdb-save-btn",
                type="button",
                cls="db-btn-primary",
                onclick="if(window._cdb) window._cdb.save();",
            ),
            cls="flex items-center gap-2",
        ),
        cls="flex items-end justify-between gap-4 mb-4 flex-wrap",
        style="padding-bottom:12px;border-bottom:1px solid #111d30;",
    )

    # ── Mobile tabs ──────────────────────────────────────────────────────────
    mobile_tabs = ft.Div(
        ft.Button("Browse", id="db-tab-browse", type="button",
                  cls="db-tab-btn active-tab",
                  onclick="window._switchBuilderTab('browse')"),
        ft.Button("My Deck", id="db-tab-deck", type="button",
                  cls="db-tab-btn",
                  onclick="window._switchBuilderTab('deck')"),
        cls="flex xl:hidden border-b mb-4",
        style="border-color:#111d30;",
    )

    return ft.Div(
        _styles(),
        ft.Div(
            page_header,
            mobile_tabs,
            # Two-panel grid
            ft.Div(
                # Left: search + filters
                ft.Div(
                    search_panel,
                    id="db-browse-panel",
                ),
                # Right: deck panel (hidden on mobile, shown via tab or xl grid)
                ft.Div(
                    deck_panel,
                    id="db-deck-panel",
                    cls="db-xl-show",
                    style="display:none;",
                ),
                cls="db-two-col",
            ),
            cls="db-page bg-deep-navy px-4 py-4 md:px-6",
        ),
        # ── Fullscreen deck overlay ──────────────────────────────────────
        ft.Div(
            ft.Div(id="db-fs-bg", cls="db-fs-bg"),
            ft.Div(cls="db-fs-vignette"),
            ft.Div(
                ft.Span("SELECT A LEADER", id="db-fs-leader-name", cls="db-fs-leader-name"),
                ft.Span(id="db-fs-total",
                        style="font-family:'Share Tech Mono',monospace;font-size:.8rem;"),
                ft.Div(
                    *[ft.Div(id=f"db-fs-bar-{i}", cls="db-fs-mini-bar", style="height:2px;")
                      for i in range(11)],
                    cls="db-fs-mini-curve",
                ),
                ft.Button("✕", type="button", cls="db-fs-close",
                          onclick="window._dbCloseFullscreen()"),
                cls="db-fs-header",
            ),
            ft.Div(id="db-fs-body", cls="db-fs-body db-scroll"),
            ft.Div(
                *[
                    ft.Button(
                        ft.Span("0", id=f"db-fs-cn-{key}", cls="db-counter-chip-val"),
                        ft.Span(label, cls="db-counter-chip-label"),
                        type="button",
                        cls="db-counter-chip",
                        id=f"db-fs-counter-{key}",
                        onclick=f"window._dbToggleCounterFilter({val})",
                        title=title,
                    )
                    for key, label, val, title in [
                        ("none", "No Counter", "null", "No counter — click to filter"),
                        ("1k",   "+1000",      "1000", "+1000 counter — click to filter"),
                        ("2k",   "+2000",      "2000", "+2000 counter — click to filter"),
                    ]
                ],
                ft.Button(
                    ft.Span("0", id="db-fs-cn-trigger", cls="db-counter-chip-val"),
                    ft.Span("Trigger", cls="db-counter-chip-label"),
                    type="button",
                    cls="db-counter-chip",
                    id="db-fs-counter-trigger",
                    onclick="window._dbToggleTriggerFilter()",
                    title="Cards with Trigger — click to filter",
                ),
                ft.Div(style="flex:1;"),
                ft.Button(
                    ft.I(cls="fas fa-random text-xs mr-1"),
                    "HAND",
                    type="button",
                    cls="db-expand-btn",
                    onclick="window._dbDrawHand()",
                ),
                *[
                    ft.Div(
                        ft.Span("0", id=f"db-fs-tc-{cat.lower()}", cls="db-fs-footer-type-val"),
                        ft.Span(cat, cls="db-fs-footer-type-label"),
                        cls="db-fs-footer-type",
                    )
                    for cat in ["Character", "Event", "Stage"]
                ],
                cls="db-fs-footer",
            ),
            id="db-fs-overlay",
            cls="db-fs-overlay",
        ),
        # ── Starting Hand overlay ────────────────────────────────────────
        ft.Div(
            ft.Div(
                ft.Div(
                    ft.Span("OPENING HAND", cls="db-hand-title-label"),
                    ft.Button("✕", type="button", cls="db-hand-close",
                              onclick="window._dbCloseHand()"),
                    cls="db-hand-header",
                ),
                ft.Span("5 CARDS — RANDOM STARTING HAND", cls="db-hand-subtitle"),
                ft.Div(id="db-hand-cards", cls="db-hand-cards"),
                ft.Div(
                    ft.Button(
                        ft.I(cls="fas fa-random mr-1.5 text-xs"),
                        "DRAW AGAIN",
                        type="button",
                        cls="db-hand-btn-draw",
                        onclick="window._dbDrawHand()",
                    ),
                    cls="db-hand-actions",
                ),
                cls="db-hand-modal",
            ),
            id="db-hand-overlay",
            cls="db-hand-overlay",
            onclick="if(event.target===this)window._dbCloseHand()",
        ),
        _page_script(prefill_data),
        cls="db-page bg-deep-navy",
    )
