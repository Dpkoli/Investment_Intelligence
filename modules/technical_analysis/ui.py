"""
Technical Analysis Module — Elliott Wave Aggregator

Tracks and links to Elliott Wave analysis across:
  Elliott Wave International · Elliott Wave Forecast · ElliottWaveTrader
  Green Star Trading · Objective Elliott Wave (Caldaro) · TradingView Ideas
  EWP Forecasting · EW Analytics
"""
from __future__ import annotations

import sys
import os

import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.technical_analysis.data import (
    PROVIDERS,
    MARKET_CATEGORIES,
    get_analysis_items,
    fetch_provider_articles,
    market_matches,
    _provider_by_id,
)

# ── Market filter config ───────────────────────────────────────────────────────

_MARKET_TABS = [
    ("All Markets",  "all",         "#5A8EBB"),
    ("Indices",      "indices",     "#0F2D4F"),
    ("Crypto",       "crypto",      "#7c3aed"),
    ("Forex",        "forex",       "#3A72A0"),
    ("Commodities",  "commodities", "#C98900"),
    ("Equities",     "equities",    "#1D4369"),
]

# ── Wave reference quick guide ─────────────────────────────────────────────────

_WAVE_GUIDE = [
    ("Impulse (5-wave)", "1-2-3-4-5",
     "Directional move in the trend direction. Wave 3 is never the shortest. Wave 4 never overlaps wave 1 price territory."),
    ("Corrective (3-wave ABC)", "A-B-C",
     "Counter-trend correction. Can take the form of a zigzag (sharp), flat (sideways), or triangle."),
    ("Extended Wave 3", "1-2-[3]-4-5",
     "The most common extended wave. Wave 3 often reaches 1.618–2.618× the length of wave 1."),
    ("Ending Diagonal", "1-2-3-4-5 (wedge)",
     "Terminal structure in wave 5 or wave C. All sub-waves are 3-wave structures. Signals exhaustion."),
    ("Triangle (ABCDE)", "A-B-C-D-E",
     "Consolidation pattern in wave 4 or wave B. Breakout (thrust) follows in the trend direction."),
    ("WXY (Double ZZ)", "W-X-Y",
     "Complex double zigzag correction. Wave X links the two three-wave structures."),
]

_DEGREE_TABLE = [
    ("Grand Supercycle", "[[I]] [[II]] [[III]] [[IV]] [[V]]",   "Centuries"),
    ("Supercycle",       "[I] [II] [III] [IV] [V]",             "Decades"),
    ("Cycle",            "I II III IV V",                        "Years"),
    ("Primary",          "(1) (2) (3) (4) (5)",                  "Months–Years"),
    ("Intermediate",     "1 2 3 4 5",                            "Weeks–Months"),
    ("Minor",            "i ii iii iv v",                        "Days–Weeks"),
    ("Minute",           "[i] [ii] [iii] [iv] [v]",             "Hours–Days"),
    ("Minuette",         "(i) (ii) (iii) (iv) (v)",             "Minutes–Hours"),
]


# ── Helper renderers ──────────────────────────────────────────────────────────

def _bias_badge(bias: str, color: str) -> str:
    if not bias:
        return ""
    return (
        f'<span style="background:{color}18;color:{color};border-radius:999px;'
        f'padding:1px 8px;font-size:0.65rem;font-weight:700;white-space:nowrap">'
        f'{bias}</span>'
    )


def _wave_badge(wave: str) -> str:
    if not wave:
        return ""
    return (
        f'<span style="background:#EEF4FB;color:#3A72A0;border-radius:6px;'
        f'padding:1px 7px;font-size:0.65rem;font-weight:700;font-family:\'JetBrains Mono\',monospace;'
        f'white-space:nowrap">{wave}</span>'
    )


def _provider_pill(provider: str, accent: str) -> str:
    return (
        f'<span style="background:{accent}15;color:{accent};border-radius:6px;'
        f'padding:1px 7px;font-size:0.63rem;font-weight:700">{provider}</span>'
    )


def _live_dot(is_live: bool) -> str:
    if is_live:
        return '<span style="width:6px;height:6px;border-radius:50%;background:#1AB868;display:inline-block;margin-right:4px;vertical-align:middle"></span>'
    return ""


def _render_analysis_card(item: dict) -> None:
    """Render a single analysis article card."""
    pid      = item.get("provider_id", "")
    prov     = item.get("provider", "—")
    title    = item.get("title", "—")
    summary  = item.get("summary", "")
    url      = item.get("url", "")
    market   = item.get("market", "")
    wave     = item.get("wave_count", "")
    bias     = item.get("bias", "")
    bcolor   = item.get("bias_color", "#5A8EBB")
    date_str = item.get("date", "—")
    is_live  = item.get("is_live", False)

    p_data  = _provider_by_id(pid)
    accent  = p_data.get("accent", "#5A8EBB") if p_data else "#5A8EBB"

    title_html = (
        f'<a href="{url}" target="_blank" rel="noopener" '
        f'style="color:#071D35;text-decoration:none;font-weight:600;font-size:0.82rem;line-height:1.45">'
        f'{title}</a>'
        if url else
        f'<span style="color:#071D35;font-weight:600;font-size:0.82rem">{title}</span>'
    )

    meta_parts = []
    if market:
        meta_parts.append(
            f'<span style="background:{accent}12;color:{accent};border-radius:4px;'
            f'padding:0 5px;font-size:0.63rem;font-weight:700">{market}</span>'
        )
    if wave:
        meta_parts.append(_wave_badge(wave))
    if bias:
        meta_parts.append(_bias_badge(bias, bcolor))

    meta_html = "  ".join(meta_parts)

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid {accent};'
        f'border-radius:0 12px 12px 0;padding:0.65rem 1rem;margin-bottom:0.4rem;'
        f'box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
        f'{title_html}'
        f'{"<div style=" + chr(39) + "color:#2B5A85;font-size:0.74rem;margin:0.25rem 0 0.2rem 0;line-height:1.5" + chr(39) + ">" + summary + "</div>" if summary else ""}'
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:0.3rem">'
        f'{_live_dot(is_live)}'
        f'{_provider_pill(prov, accent)}'
        f'{meta_html}'
        f'<span style="color:#5A8EBB;font-size:0.65rem;margin-left:auto">{date_str}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_provider_card(p: dict) -> None:
    """Render a provider profile card."""
    accent = p.get("accent", "#5A8EBB")
    color  = p.get("color", "#0F2D4F")

    # Coverage chips
    coverage_html = " ".join(
        f'<span style="background:#EEF4FB;color:#2B5A85;border-radius:4px;'
        f'padding:0 6px;font-size:0.62rem;margin:1px;display:inline-block">{mkt}</span>'
        for mkt in p.get("coverage", [])
    )

    # Tier badge
    tier = p.get("tier", "")
    tier_color = (
        "#149453" if "Free" in tier and "Paid" not in tier else
        "#E8A500" if "Freemium" in tier else
        "#E53535" if "Paid" in tier else
        "#5A8EBB"
    )

    # Links
    links = []
    if p.get("free_url"):
        links.append(f'<a href="{p["free_url"]}" target="_blank" rel="noopener" '
                     f'style="color:{accent};font-size:0.72rem;font-weight:600;text-decoration:none;'
                     f'background:{accent}10;padding:2px 8px;border-radius:6px">Visit site ↗</a>')
    if p.get("twitter_url"):
        links.append(f'<a href="{p["twitter_url"]}" target="_blank" rel="noopener" '
                     f'style="color:#5A8EBB;font-size:0.72rem;text-decoration:none">Twitter/X</a>')
    if p.get("youtube_url"):
        links.append(f'<a href="{p["youtube_url"]}" target="_blank" rel="noopener" '
                     f'style="color:#E53535;font-size:0.72rem;text-decoration:none">YouTube</a>')

    links_html = "  ·  ".join(links)

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {accent};'
        f'border-radius:0 0 12px 12px;padding:1rem 1.1rem;height:100%;box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
        # Header
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem">'
        f'<div>'
        f'<div style="font-weight:700;font-size:0.9rem;color:#071D35">{p["name"]}</div>'
        f'<div style="color:#5A8EBB;font-size:0.68rem;margin-top:1px">est. {p.get("founded","—")} · {p.get("analyst","—")}</div>'
        f'</div>'
        f'<span style="background:{tier_color}18;color:{tier_color};border-radius:999px;'
        f'padding:2px 8px;font-size:0.62rem;font-weight:700;white-space:nowrap">{tier}</span>'
        f'</div>'
        # Description
        f'<div style="color:#2B5A85;font-size:0.76rem;line-height:1.55;margin-bottom:0.55rem">{p["description"]}</div>'
        # Coverage
        f'<div style="margin-bottom:0.5rem">{coverage_html}</div>'
        # Links
        f'<div style="display:flex;gap:8px;flex-wrap:wrap">{links_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _render_providers_tab() -> None:
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:#5A8EBB;'
        'text-transform:uppercase;margin-bottom:0.6rem">'
        f'{len(PROVIDERS)} tracked providers · click Visit site for analysis</p>',
        unsafe_allow_html=True,
    )

    # 2-column grid
    for i in range(0, len(PROVIDERS), 2):
        cols = st.columns(2, gap="medium")
        for col, p in zip(cols, PROVIDERS[i:i+2]):
            with col:
                _render_provider_card(p)
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)


def _render_analysis_tab(market_key: str, market_label: str, accent: str) -> None:
    """Render the analysis list for a given market filter."""

    c1, c2 = st.columns([8, 1])
    with c1:
        search = st.text_input(
            "Search", key=f"ta_search_{market_key}",
            placeholder="Search by title, wave count, market or analyst…",
            label_visibility="collapsed",
        )
    with c2:
        if st.button("Refresh", key=f"ta_refresh_{market_key}", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Loading analysis…"):
        all_items = get_analysis_items()

    # Filter by market
    items = [i for i in all_items if market_matches(i, market_key)]

    # Filter by search
    q = (search or "").strip().lower()
    if q:
        items = [
            i for i in items
            if q in i.get("title", "").lower()
            or q in i.get("summary", "").lower()
            or q in i.get("market", "").lower()
            or q in i.get("wave_count", "").lower()
            or q in i.get("provider", "").lower()
        ]

    if not items:
        st.info(
            f"No analysis entries for {market_label}"
            + (" matching your search." if q else ". Try another market tab.")
        )
        return

    live_count = sum(1 for i in items if i.get("is_live"))
    static_count = len(items) - live_count

    status_parts = [f"{len(items)} analysis entries"]
    if live_count:
        status_parts.append(f"{live_count} live from RSS")
    if static_count:
        status_parts.append(f"{static_count} curated")

    st.markdown(
        f'<p style="font-size:0.68rem;color:#5A8EBB;margin-bottom:0.4rem">'
        f'{"  ·  ".join(status_parts)}</p>',
        unsafe_allow_html=True,
    )

    for item in items:
        _render_analysis_card(item)


def _render_live_feed_tab() -> None:
    """Show live RSS articles only."""
    if st.button("Refresh live feeds", key="ta_live_refresh"):
        st.cache_data.clear()
        st.rerun()

    # Show which providers have RSS
    rss_providers = [p for p in PROVIDERS if p.get("rss")]
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;color:#5A8EBB;'
        'text-transform:uppercase;margin-bottom:0.4rem">'
        f'Live RSS: {", ".join(p["short"] for p in rss_providers)}</p>',
        unsafe_allow_html=True,
    )

    with st.spinner("Fetching live analysis feeds…"):
        live_items = [i for i in get_analysis_items() if i.get("is_live")]

    if not live_items:
        st.info(
            "No live articles fetched at this time. RSS feeds may be temporarily unavailable, "
            "rate-limited, or the network may be restricted. Curated analysis is shown in all other tabs."
        )
        # Show provider links so user can visit directly
        st.markdown(
            '<p style="font-size:0.73rem;color:#2B5A85;margin-top:0.5rem">'
            'Visit providers directly:</p>',
            unsafe_allow_html=True,
        )
        for p in rss_providers:
            st.markdown(
                f'<a href="{p["free_url"]}" target="_blank" rel="noopener" '
                f'style="display:block;color:{p["accent"]};font-weight:600;font-size:0.8rem;'
                f'margin-bottom:0.2rem;text-decoration:none">'
                f'↗ {p["name"]}</a>',
                unsafe_allow_html=True,
            )
        return

    for item in live_items:
        _render_analysis_card(item)


def _render_wave_guide_tab() -> None:
    """Render Elliott Wave quick reference guide."""
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:#5A8EBB;'
        'text-transform:uppercase;margin-bottom:0.75rem">Wave Patterns — Quick Reference</p>',
        unsafe_allow_html=True,
    )

    g1, g2 = st.columns(2, gap="medium")

    for idx, (name, label, desc) in enumerate(_WAVE_GUIDE):
        with (g1 if idx % 2 == 0 else g2):
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid #3A72A0;'
                f'border-radius:0 12px 12px 0;padding:0.7rem 1rem;margin-bottom:0.45rem;'
                f'box-shadow:0 1px 3px rgba(7,29,53,0.04)">'
                f'<div style="font-weight:700;font-size:0.82rem;color:#071D35;margin-bottom:0.2rem">{name}</div>'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.75rem;color:#3A72A0;'
                f'background:#EEF4FB;padding:2px 8px;border-radius:4px;display:inline-block;margin-bottom:0.3rem">{label}</div>'
                f'<div style="color:#2B5A85;font-size:0.74rem;line-height:1.5">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:#5A8EBB;'
        'text-transform:uppercase;margin:1rem 0 0.6rem 0">Wave Degree Hierarchy</p>',
        unsafe_allow_html=True,
    )

    deg_header = (
        '<div style="display:grid;grid-template-columns:140px 1fr 90px;gap:0;'
        'background:#EEF4FB;border:1px solid #D9E8F5;border-radius:8px 8px 0 0;'
        'padding:0.35rem 0.9rem">'
        '<span style="font-size:0.68rem;font-weight:700;color:#5A8EBB;text-transform:uppercase;letter-spacing:0.06em">Degree</span>'
        '<span style="font-size:0.68rem;font-weight:700;color:#5A8EBB;text-transform:uppercase;letter-spacing:0.06em">Labels</span>'
        '<span style="font-size:0.68rem;font-weight:700;color:#5A8EBB;text-transform:uppercase;letter-spacing:0.06em">Timeframe</span>'
        '</div>'
    )
    st.markdown(deg_header, unsafe_allow_html=True)

    for i, (degree, labels, timeframe) in enumerate(_DEGREE_TABLE):
        bg = "#ffffff" if i % 2 == 0 else "#F7FAFD"
        radius = "0 0 8px 8px" if i == len(_DEGREE_TABLE) - 1 else "0"
        st.markdown(
            f'<div style="display:grid;grid-template-columns:140px 1fr 90px;gap:0;'
            f'background:{bg};border:1px solid #D9E8F5;border-top:none;'
            f'border-radius:{radius};padding:0.32rem 0.9rem">'
            f'<span style="font-size:0.74rem;font-weight:600;color:#071D35">{degree}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.71rem;color:#3A72A0">{labels}</span>'
            f'<span style="font-size:0.72rem;color:#5A8EBB">{timeframe}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="font-size:0.72rem;color:#5A8EBB;margin-top:0.75rem;line-height:1.6">'
        '<b style="color:#2B5A85">Key rules:</b> &nbsp;'
        'Wave 2 never retraces more than 100% of wave 1. &nbsp;·&nbsp; '
        'Wave 3 is never the shortest impulse wave. &nbsp;·&nbsp; '
        'Wave 4 never enters the price territory of wave 1. &nbsp;·&nbsp; '
        'In a triangle, all sub-waves are three-wave structures.'
        '</p>',
        unsafe_allow_html=True,
    )


# ── Main entry ────────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown(
        "<h2 class='iw-module-header'>Technical Analysis — Elliott Wave Intelligence</h2>"
        "<p style='color:#5A8EBB;margin-top:2px;font-size:0.82rem'>"
        "Aggregated Elliott Wave analysis from leading providers across the internet · "
        "updated hourly · click any headline to read the original</p>",
        unsafe_allow_html=True,
    )

    # ── Provider status bar ───────────────────────────────────────────────────
    rss_count = sum(1 for p in PROVIDERS if p.get("rss"))
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin:0.6rem 0 0.9rem 0">'
        + "".join(
            f'<a href="{p["free_url"]}" target="_blank" rel="noopener" '
            f'style="display:inline-flex;align-items:center;gap:4px;background:{p["accent"]}12;'
            f'color:{p["accent"]};border:1px solid {p["accent"]}30;border-radius:999px;'
            f'padding:3px 10px;font-size:0.67rem;font-weight:700;text-decoration:none;white-space:nowrap">'
            f'{"<span style=" + chr(39) + "width:5px;height:5px;border-radius:50%;background:" + p["accent"] + ";flex-shrink:0" + chr(39) + "></span>" if p.get("rss") else ""}'
            f'{p["short"]} ↗</a>'
            for p in PROVIDERS
        )
        + f'<span style="color:#5A8EBB;font-size:0.65rem;align-self:center;margin-left:4px">'
        f'{rss_count} live RSS feeds enabled</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_labels = (
        ["Providers"] +
        [label for label, _, _ in _MARKET_TABS] +
        ["Live RSS", "Wave Guide"]
    )
    tabs = st.tabs(tab_labels)

    tab_iter = iter(tabs)

    # Providers tab
    with next(tab_iter):
        _render_providers_tab()

    # Market tabs
    for (label, key, accent), tab_obj in zip(_MARKET_TABS, tab_iter):
        with tab_obj:
            _render_analysis_tab(key, label, accent)

    # Live RSS tab
    with next(tab_iter):
        _render_live_feed_tab()

    # Wave Guide tab
    with next(tab_iter):
        _render_wave_guide_tab()
