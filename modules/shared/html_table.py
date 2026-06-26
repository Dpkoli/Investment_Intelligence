"""Shared reusable HTML table with full-row click selection via hidden channel input."""
from __future__ import annotations
import html as _html
from typing import Optional
import streamlit as st

_CSS = """<style>
.iw-tbl-w{border:1px solid #D9E8F5;border-radius:10px;overflow-x:auto;
  box-shadow:0 1px 3px rgba(7,29,53,0.05);background:#fff}
.iw-tbl{width:100%;border-collapse:collapse;font-size:0.82rem;
  font-family:'Plus Jakarta Sans',system-ui,sans-serif}
.iw-tbl th{background:#EEF4FB;color:#071D35;font-weight:700;font-size:0.77rem;
  padding:0.5rem 0.75rem;text-align:left;border-bottom:2px solid #D9E8F5;white-space:nowrap}
.iw-tbl th:first-child{width:38px;padding:0.5rem 0.6rem;text-align:center}
.iw-row{cursor:pointer;border-bottom:1px solid #EEF4FB;transition:background 0.08s}
.iw-row:hover{background:#F5F9FF}
.iw-row.iw-sel{background:#EDFAF3}
.iw-tbl td{padding:0.42rem 0.75rem;color:#071D35;white-space:nowrap;font-size:0.82rem}
.iw-tbl td:first-child{padding:0.42rem 0.6rem;text-align:center}
.td-muted{color:#5A8EBB!important}
.td-pos{color:#149453!important;font-weight:600}
.td-neg{color:#E53535!important;font-weight:600}
.td-warn{color:#E8A500!important;font-weight:600}
.td-mono{font-family:'JetBrains Mono',monospace!important;font-size:0.79rem!important}
.iw-cb{accent-color:#1AB868;cursor:default;width:14px;height:14px;pointer-events:none;vertical-align:middle}
</style>"""

_JS = """<script>
(function(){
  if(window._iwTblReady)return;
  window._iwTblReady=true;
  window.iwTblClick=function(ph,idx,event){
    if(event&&event.target&&event.target.type==='checkbox')return;
    var doc=document;
    var ch=null;
    var inputs=doc.querySelectorAll('[data-testid="stTextInput"] input');
    for(var i=0;i<inputs.length;i++){if(inputs[i].placeholder===ph){ch=inputs[i];break;}}
    if(!ch)return;
    var s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
    s.call(ch,String(idx));
    ch.dispatchEvent(new Event('input',{bubbles:true}));
    ch.dispatchEvent(new Event('change',{bubbles:true}));
    setTimeout(function(){
      ch.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));
      ch.blur();
    },30);
  };
})();
</script>"""


def render(
    rows: list[dict],
    columns: list,
    channel_placeholder: str,
    selected_idx: Optional[int] = None,
    col_classes: Optional[dict] = None,
) -> Optional[int]:
    """Render a selectable HTML table and return the newly-clicked row index or None.

    Args:
        rows: List of dicts with cell data.
        columns: List of column names (str) or (key, header_label) tuples.
        channel_placeholder: Unique placeholder for the hidden channel input.
                             Must start with 'iw-tbl-' so the global CSS hides it.
        selected_idx: Index of the currently-selected row (for highlight / checkbox).
        col_classes: Dict mapping column key → CSS class string (td-muted, td-pos, etc.).

    Returns:
        Newly-selected row index communicated by JS, or None if nothing clicked.
    """
    # Normalise columns to (key, label) pairs
    cols: list[tuple[str, str]] = [
        (c, c) if isinstance(c, str) else tuple(c)  # type: ignore[arg-type]
        for c in columns
    ]
    col_classes = col_classes or {}

    # Hidden channel input
    _ch_key = f"_iwtbl_{channel_placeholder}"
    if st.session_state.pop(f"_iwtbl_clear_{_ch_key}", False):
        st.session_state.pop(_ch_key, None)

    raw: str = st.text_input(
        "_t", key=_ch_key,
        placeholder=channel_placeholder,
        label_visibility="collapsed",
    )

    # Read selection from channel
    new_sel: Optional[int] = None
    raw = (raw or "").strip()
    if raw and raw.lstrip("-").isdigit():
        v = int(raw)
        if v >= 0:
            new_sel = v

    # Build header row
    header_cells = "<th></th>" + "".join(f"<th>{h}</th>" for _, h in cols)

    # Build body rows
    body: list[str] = []
    for i, row in enumerate(rows):
        is_sel = (selected_idx == i)
        row_cls = "iw-row iw-sel" if is_sel else "iw-row"
        checked = "checked" if is_sel else ""
        cells = [f'<td><input type="checkbox" class="iw-cb" {checked}></td>']
        for key, _ in cols:
            raw_val = row.get(key, "—")
            val = _html.escape(str(raw_val)) if raw_val is not None else "—"
            cls = col_classes.get(key, "")
            cls_attr = f' class="{cls}"' if cls else ""
            cells.append(f"<td{cls_attr}>{val}</td>")
        # Use data attributes instead of onclick — DOMPurify strips <script> and onclick
        data_attrs = f'data-ph="{_html.escape(channel_placeholder)}" data-idx="{i}"'
        body.append(f'<tr class="{row_cls}" {data_attrs}>{"".join(cells)}</tr>')

    # Do NOT include _JS here — <script> tags are stripped by DOMPurify in st.markdown
    # and corrupt the surrounding HTML. JS wiring lives in the global components.html block.
    html = (
        _CSS +
        '<div class="iw-tbl-w"><table class="iw-tbl">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)
    return new_sel
