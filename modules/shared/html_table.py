"""Shared reusable table using native Streamlit dataframe row-selection."""
from __future__ import annotations
from typing import Optional
import pandas as pd
import streamlit as st


def render(
    rows: list[dict],
    columns: list,
    channel_placeholder: str,
    selected_idx: Optional[int] = None,
    col_classes: Optional[dict] = None,
) -> Optional[int]:
    """Render a selectable table; returns the currently-selected row index or None.

    Uses st.dataframe with on_select='rerun' so selection is fully native.
    The channel_placeholder is used as a stable widget key prefix.
    """
    cols: list[tuple[str, str]] = [
        (c, c) if isinstance(c, str) else tuple(c)
        for c in columns
    ]

    df = pd.DataFrame([
        {label: row.get(key, "—") for key, label in cols}
        for row in rows
    ])

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"df_{channel_placeholder}",
    )

    sel = getattr(getattr(event, "selection", None), "rows", [])
    return sel[0] if sel else None
