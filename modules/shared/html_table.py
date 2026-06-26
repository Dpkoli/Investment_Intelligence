"""Shared reusable table using native Streamlit dataframe row-selection.

Row selection is captured via st.dataframe(on_select='rerun', selection_mode='single-row').
A thin "▶" selector column is prepended so users have an unambiguous, non-text click
target that reliably fires the row-selection event rather than AG Grid's cell-focus mode.
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
import streamlit as st

_SEL_COL = "▶"


def render(
    rows: list[dict],
    columns: list,
    channel_placeholder: str,
    selected_idx: Optional[int] = None,
    col_classes: Optional[dict] = None,
) -> Optional[int]:
    """Render a selectable table; returns the currently-selected row index or None.

    Prepends a thin '▶' selector column as a reliable whole-row click target.
    Clicking any column (including the selector) fires event.selection.rows.
    """
    cols: list[tuple[str, str]] = [
        (c, c) if isinstance(c, str) else tuple(c)
        for c in columns
    ]

    df = pd.DataFrame([
        {
            _SEL_COL: "▶",
            **{label: row.get(key, "—") for key, label in cols},
        }
        for row in rows
    ])

    col_cfg: dict = {
        _SEL_COL: st.column_config.TextColumn(
            label="",
            width="small",
            help="Click to select row",
        ),
    }

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"df_{channel_placeholder}",
        column_config=col_cfg,
        column_order=[_SEL_COL] + [label for _, label in cols],
    )

    sel = getattr(getattr(event, "selection", None), "rows", [])
    return sel[0] if sel else None
