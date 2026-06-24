"""
Shared typeahead autocomplete widget for InvestWise dropdowns.

Usage:
    from modules.shared import inject_autocomplete

    items = [{"l": "BTC-USD — Bitcoin", "v": "BTC-USD",
              "b": "Crypto", "s": "btc-usd bitcoin crypto"}]
    inject_autocomplete(json.dumps(items), "My search placeholder…")

Each item dict:
    l  — display label (HTML-safe; substring highlighting is applied automatically)
    v  — value written back to the Streamlit text_input on selection
    b  — badge label shown on the right (optional, e.g. category/row)
    s  — lowercase searchable string (ticker + name + tags, space-separated)

Keyboard behaviour (applied globally whenever this function is called):
    ↓ / ↑  — move highlight through visible rows
    Enter   — select highlighted row (or dismiss if none highlighted)
    Escape  — dismiss without selecting
"""

from __future__ import annotations


def inject_autocomplete(items_json: str, placeholder: str) -> None:
    """Inject a typeahead dropdown bound to the text input with *placeholder*."""
    import streamlit.components.v1 as components

    ph = placeholder.replace("'", "\\'")
    components.html(f"""<script>
(function(){{
  var DATA={items_json};
  var PH="{ph}";
  var doc=window.parent.document;

  /* ── helpers ─────────────────────────────────────────────────────────── */
  function findInput(){{
    var els=doc.querySelectorAll('[data-testid="stTextInput"] input');
    for(var i=0;i<els.length;i++){{ if(els[i].placeholder===PH) return els[i]; }}
    return null;
  }}

  /* React-safe value setter — direct assignment bypasses React's synthetic event */
  function setReactVal(inp,val){{
    var setter=Object.getOwnPropertyDescriptor(
      window.parent.HTMLInputElement.prototype,'value').set;
    setter.call(inp,val);
    inp.dispatchEvent(new Event('input',{{bubbles:true,composed:true}}));
  }}

  function hl(t,q){{
    if(!q) return t;
    var re=new RegExp('('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','gi');
    return t.replace(re,
      '<mark style="background:#D9E8F5;color:#0F2D4F;border-radius:2px;padding:0 1px">$1</mark>');
  }}

  /* ── attach ──────────────────────────────────────────────────────────── */
  function attach(input){{
    if(input._iwAC) return;
    input._iwAC=true;

    var wrap=input.closest('[data-testid="stTextInput"]');
    if(!wrap) return;
    wrap.style.position='relative';

    var drop=doc.createElement('div');
    drop.style.cssText=
      'position:absolute;top:calc(100% + 3px);left:0;right:0;'
      +'background:#fff;border:1.5px solid #D9E8F5;border-radius:8px;'
      +'box-shadow:0 4px 16px rgba(7,29,53,.12);z-index:99999;'
      +'max-height:264px;overflow-y:auto;display:none;'
      +'font-family:Plus Jakarta Sans,system-ui,sans-serif;font-size:0.83rem;';
    wrap.appendChild(drop);

    var activeIdx=-1;

    function rows(){{ return drop.querySelectorAll('.iw-ac-row'); }}

    function setActive(idx){{
      var rs=rows();
      rs.forEach(function(r,i){{
        r.style.background=i===idx?'#D9E8F5':'';
      }});
      activeIdx=idx;
      if(idx>=0&&rs[idx]) rs[idx].scrollIntoView({{block:'nearest'}});
    }}

    function selectRow(row){{
      setReactVal(input,row.getAttribute('data-v'));
      drop.style.display='none';
      activeIdx=-1;
      setTimeout(function(){{
        input.dispatchEvent(new KeyboardEvent('keydown',{{
          key:'Enter',code:'Enter',keyCode:13,which:13,
          bubbles:true,cancelable:true,composed:true
        }}));
      }},80);
    }}

    function update(){{
      var q=input.value.trim().toLowerCase();
      if(!q){{ drop.style.display='none'; activeIdx=-1; return; }}
      var hits=DATA.filter(function(it){{ return it.s.includes(q); }}).slice(0,10);
      if(!hits.length){{ drop.style.display='none'; activeIdx=-1; return; }}
      drop.innerHTML=hits.map(function(it,i){{
        var border=i<hits.length-1?'border-bottom:1px solid #EEF4FB;':'';
        return '<div class="iw-ac-row" data-v="'+it.v.replace(/"/g,'&quot;')+'" style="'
          +'display:flex;justify-content:space-between;align-items:center;'
          +'padding:0.45rem 0.9rem;cursor:pointer;'+border+'">'
          +'<span style="color:#071D35;font-weight:500">'+hl(it.l,q)+'</span>'
          +(it.b
            ?'<span style="font-size:0.68rem;color:#5A8EBB;background:#EEF4FB;'
              +'padding:1px 7px;border-radius:4px;white-space:nowrap;margin-left:8px">'+it.b+'</span>'
            :'')
          +'</div>';
      }}).join('');
      rows().forEach(function(row,i){{
        row.addEventListener('mouseenter',function(){{ setActive(i); }});
        row.addEventListener('mouseleave',function(){{ row.style.background=''; activeIdx=-1; }});
        row.addEventListener('mousedown',function(e){{
          e.preventDefault();
          selectRow(row);
        }});
      }});
      drop.style.display='block';
      activeIdx=-1;
    }}

    /* ── keyboard navigation ─────────────────────────────────────────────── */
    input.addEventListener('keydown',function(e){{
      var rs=rows();
      var visible=drop.style.display!=='none'&&rs.length>0;
      if(e.key==='ArrowDown'){{
        if(!visible) return;
        e.preventDefault();
        setActive(Math.min(activeIdx+1,rs.length-1));
      }} else if(e.key==='ArrowUp'){{
        if(!visible) return;
        e.preventDefault();
        setActive(Math.max(activeIdx-1,0));
      }} else if(e.key==='Enter'){{
        if(visible&&activeIdx>=0&&rs[activeIdx]){{
          e.preventDefault();
          e.stopPropagation();
          selectRow(rs[activeIdx]);
        }} else {{
          drop.style.display='none';
          activeIdx=-1;
        }}
      }} else if(e.key==='Escape'){{
        drop.style.display='none';
        activeIdx=-1;
      }}
    }});

    input.addEventListener('input',update);
    input.addEventListener('focus',function(){{ if(input.value) update(); }});
    input.addEventListener('blur',function(){{
      setTimeout(function(){{ drop.style.display='none'; activeIdx=-1; }},200);
    }});
  }}

  function init(){{ var inp=findInput(); if(inp) attach(inp); }}
  init();
  new MutationObserver(init).observe(doc.body,{{childList:true,subtree:true}});
}})();
</script>""", height=0, scrolling=False)
