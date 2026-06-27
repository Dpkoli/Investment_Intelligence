"""Authentication page and gate logic for InvestWise."""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

_FREE_MODULES   = {"Intelligence Hub", "News Feed"}
_AUTH_PAGE_KEY  = "_iw_show_auth_page"
_SA_PARAM       = "iw-sa-admin-portal-2025"   # secret URL ?_portal=<value>
_SA_SECRET      = "iw-internal-sa-key-9x7z"   # superadmin password
_REDIRECT_URL   = "https://st-wise.streamlit.app"


# ─────────────────────────────────────────────────────────────────────────────
# Core state helpers
# ─────────────────────────────────────────────────────────────────────────────

def check_auth() -> bool:
    return bool(st.session_state.get("is_authenticated", False))


def is_superadmin() -> bool:
    return st.session_state.get("user_role") == "superadmin"


def mock_login(email: str, display_name: str = "", role: str = "user") -> None:
    st.session_state["is_authenticated"] = True
    st.session_state["user_email"]       = email
    st.session_state["user_name"]        = display_name or email.split("@")[0].title()
    st.session_state["user_role"]        = role
    st.session_state.pop(_AUTH_PAGE_KEY, None)   # clear auth-page flag → land in module


def logout() -> None:
    for k in ("is_authenticated", "user_email", "user_name", "user_role",
              _AUTH_PAGE_KEY, "_oauth_redirect"):
        st.session_state.pop(k, None)


def is_free_module(nav: str) -> bool:
    return nav in _FREE_MODULES


def request_auth_page() -> None:
    st.session_state[_AUTH_PAGE_KEY] = True
    st.rerun()


def wants_auth_page() -> bool:
    return bool(st.session_state.get(_AUTH_PAGE_KEY)) and not check_auth()


# ─────────────────────────────────────────────────────────────────────────────
# Supabase client
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _supabase():
    """Return a cached Supabase client, or a string error message on failure."""
    try:
        from supabase import create_client  # lazy — prevents startup crash if not installed
    except ImportError:
        return "pkg_missing"

    # Read keys from the root level of st.secrets (not under any [section] header)
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError as exc:
        return f"secrets_missing:{exc}"

    try:
        return create_client(url, key)
    except Exception as exc:
        return f"client_error:{exc}"


def _supabase_client_or_error():
    """Return (client, None) on success, or (None, error_message) on failure."""
    result = _supabase()
    if isinstance(result, str):
        if result == "pkg_missing":
            msg = "The `supabase` Python package is not installed."
        elif result.startswith("secrets_missing:"):
            missing = result.split(":", 1)[1]
            msg = (
                f"Secret {missing} not found. "
                "Go to Streamlit Cloud → your app → Settings → Secrets and add:\n\n"
                "```\nSUPABASE_URL = \"https://your-project.supabase.co\"\n"
                "SUPABASE_KEY = \"your-anon-public-key\"\n```"
            )
        else:
            msg = f"Supabase client error: {result.split(':', 1)[1]}"
        return None, msg
    return result, None


def _get_oauth_url(provider: str) -> str | None:
    """Ask Supabase for an OAuth redirect URL without auto-opening a browser."""
    sb, err = _supabase_client_or_error()
    if err:
        st.error(err, icon="⚠️")
        return None
    try:
        resp = sb.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": _REDIRECT_URL,
                "skip_browser_redirect": True,
            },
        })
        return getattr(resp, "url", None)
    except Exception as exc:
        st.error(f"Could not start {provider} sign-in: {exc}", icon="⚠️")
        return None


def _handle_oauth_callback() -> bool:
    """Exchange a PKCE ?code= param for a real Supabase session.

    Returns True when the user has been logged in so the caller can rerun.
    """
    code = st.query_params.get("code")
    if not code:
        return False
    sb, _ = _supabase_client_or_error()   # silently skip if not configured
    if sb is None:
        return False
    try:
        result = sb.auth.exchange_code_for_session({"auth_code": code})
        user = getattr(result, "user", None)
        if user:
            meta = getattr(user, "user_metadata", {}) or {}
            name = (
                meta.get("full_name")
                or meta.get("name")
                or (user.email or "").split("@")[0].title()
            )
            mock_login(email=user.email or "", display_name=name)
            try:
                st.query_params.clear()
            except Exception:
                pass
            return True
    except Exception as exc:
        st.error(f"Sign-in completion failed: {exc}", icon="⚠️")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Brand SVG icons (inline, no external dependencies)
# ─────────────────────────────────────────────────────────────────────────────

_AUTH_CSS = """<style>
/* ── Auth page page-level reset ─────────────────────────────────────── */
.iw-auth-wrap {
    max-width: 480px;
    margin: 0 auto;
    padding-bottom: 2rem;
}
/* Divider between social and email */
.iw-or-divider {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1rem 0 0.9rem;
    color: #5A8EBB;
    font-size: 0.76rem;
}
.iw-or-divider::before,
.iw-or-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #D9E8F5;
}
/* ── Superadmin: hide social channel inputs ─────────────────────────── */
[data-testid="stTextInput"]:has(input[placeholder^="iw-auth-social-"]) {
    position: fixed !important;
    left: -9999px !important;
    top:  -9999px !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
/* ── Superadmin badge ───────────────────────────────────────────────── */
.iw-sa-badge {
    background: #071D35;
    color: #1AB868;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 0.6rem;
}
</style>"""


_SOCIAL_BTN_HTML = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  .btn-row { display: flex; gap: 10px; width: 100%; }
  .oauth-btn {
    flex: 1; display: flex; align-items: center; justify-content: center;
    gap: 10px; padding: 10px 14px; border-radius: 8px;
    font-size: 14px; font-weight: 500; cursor: pointer;
    border: none; transition: opacity 0.15s, box-shadow 0.15s;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .oauth-btn:hover { opacity: 0.88; box-shadow: 0 2px 8px rgba(0,0,0,0.18); }
  .oauth-btn:active { opacity: 0.75; }
  .btn-google { background: #ffffff; color: #3c4043; border: 1.5px solid #dadce0; }
  .btn-github { background: #24292e; color: #ffffff; border: 1.5px solid #24292e; }
  svg { flex-shrink: 0; }
</style>
<div class="btn-row">
  <button class="oauth-btn btn-google" onclick="sendClick('google')">
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
      <path fill="none" d="M0 0h48v48H0z"/>
    </svg>
    Continue with Google
  </button>
  <button class="oauth-btn btn-github" onclick="sendClick('github')">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="#ffffff">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
    </svg>
    Continue with GitHub
  </button>
</div>
<script>
function sendClick(provider) {
  var doc = window.parent.document;
  var inputs = doc.querySelectorAll('input[placeholder^="iw-auth-social-"]');
  if (!inputs.length) { return; }
  var inp = inputs[0];
  var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  nativeSetter.call(inp, provider);
  inp.dispatchEvent(new Event('input',  { bubbles: true }));
  inp.dispatchEvent(new Event('change', { bubbles: true }));
  inp.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', keyCode: 13 }));
}
</script>
"""

_SOCIAL_BTN_HEIGHT = 60   # px — enough for one button row


def _render_social_buttons() -> None:
    """Render Google + GitHub OAuth buttons with branded SVG logos."""
    # ── Redirect panel: a provider was already chosen ─────────────────────────
    if "_oauth_redirect" in st.session_state:
        provider, oauth_url = st.session_state["_oauth_redirect"]
        icon  = "🌐" if provider == "google" else "💻"
        label = "Google" if provider == "google" else "GitHub"

        st.info(
            f"Click the button below to open the {label} sign-in page. "
            f"You'll be returned here automatically after signing in.",
            icon=icon,
        )
        st.link_button(
            f"Open {label} sign-in →",
            url=oauth_url,
            type="primary",
            use_container_width=True,
        )
        if st.button("← Choose a different method", key="_oauth_back",
                     use_container_width=True):
            st.session_state.pop("_oauth_redirect", None)
            st.rerun()
        return

    # ── Hidden text_input: receives provider name from iframe JS ──────────────
    # The placeholder prefix "iw-auth-social-" is used by the JS selector;
    # CSS in _AUTH_CSS visually hides this input off-screen.
    clicked = st.text_input(
        "oauth_channel",
        value="",
        placeholder="iw-auth-social-channel",
        key="_oauth_channel_input",
        label_visibility="collapsed",
    )

    # ── Branded iframe buttons ────────────────────────────────────────────────
    components.html(_SOCIAL_BTN_HTML, height=_SOCIAL_BTN_HEIGHT, scrolling=False)

    # ── React to a click that arrived this render cycle ───────────────────────
    if clicked in ("google", "github"):
        # Clear the channel so the next render doesn't re-fire
        st.session_state["_oauth_channel_input"] = ""
        url = _get_oauth_url(clicked)
        if url:
            st.session_state["_oauth_redirect"] = (clicked, url)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Superadmin panel (hidden — accessed via ?_portal=<secret>)
# ─────────────────────────────────────────────────────────────────────────────

def _is_superadmin_portal() -> bool:
    try:
        return st.query_params.get("_portal", "") == _SA_PARAM
    except Exception:
        return False


def _render_superadmin_panel() -> None:
    st.markdown(
        '<div class="iw-sa-badge">⬡ SUPERADMIN PORTAL</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#5A8EBB;font-size:0.82rem;margin:0 0 1rem 0">'
        'This panel is for internal administrators only. '
        'All activity is logged.</p>',
        unsafe_allow_html=True,
    )
    sa_key = st.text_input(
        "Admin secret key", type="password",
        placeholder="Enter administrator key", key="_sa_key_input",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Authenticate as Superadmin", type="primary",
                     use_container_width=True, key="_sa_login_btn"):
            if sa_key == _SA_SECRET:
                mock_login("superadmin@investwise.internal", "Superadmin", role="superadmin")
                st.success("Superadmin access granted.")
                st.rerun()
            else:
                st.error("Invalid key.")
    with c2:
        if st.button("Cancel", use_container_width=True, key="_sa_cancel_btn"):
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state.pop(_AUTH_PAGE_KEY, None)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Lock screen (gate card — no form embedded)
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_gate(module_name: str) -> None:
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;'
        f'border-top:3px solid #1AB868;border-radius:12px;'
        f'padding:2.5rem 2rem 2rem;max-width:460px;margin:4rem auto;text-align:center;'
        f'box-shadow:0 4px 20px rgba(7,29,53,0.08)">'
        f'<div style="font-size:2.4rem;margin-bottom:0.6rem">🔒</div>'
        f'<h3 style="color:#071D35;font-weight:800;font-size:1.15rem;'
        f'margin:0 0 0.5rem 0">{module_name}</h3>'
        f'<p style="color:#5A8EBB;font-size:0.88rem;margin:0 0 1.5rem 0;line-height:1.6">'
        f'This module requires a free account. Sign in to unlock all premium intelligence '
        f'features — Intelligence Hub and News Feed are always free.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button(
            "Sign In / Create Account →",
            type="primary",
            use_container_width=True,
            key=f"_auth_gate_cta_{module_name.replace(' ', '_')}",
        ):
            request_auth_page()


# ─────────────────────────────────────────────────────────────────────────────
# Dedicated auth page (full design)
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page() -> None:
    # Inject page-scoped CSS
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # ── Superadmin portal (hidden route) ──────────────────────────────────────
    if _is_superadmin_portal():
        _render_superadmin_panel()
        return

    # ── Handle OAuth callback (PKCE ?code= redirect from provider) ────────────
    if _handle_oauth_callback():
        st.rerun()

    # ── Back navigation ───────────────────────────────────────────────────────
    if st.button("← Back", key="_auth_back_btn"):
        st.session_state.pop(_AUTH_PAGE_KEY, None)
        st.session_state.pop("_oauth_redirect", None)
        st.rerun()

    # ── InvestWise branded header ─────────────────────────────────────────────
    st.markdown(
        '<div class="iw-auth-wrap">'
        '<div style="text-align:center;padding:1.5rem 0 1.2rem">'
        '<div style="display:inline-flex;align-items:center;gap:8px;margin-bottom:0.6rem">'
        '<div style="width:36px;height:36px;border-radius:9px;background:#071D35;'
        'display:flex;align-items:center;justify-content:center">'
        '<svg width="20" height="20" viewBox="0 0 32 32" fill="none">'
        '<polyline points="3,24 9,17 14,20 20,12 28,7" stroke="#1AB868" '
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="28" cy="7" r="2.5" fill="#1AB868"/>'
        '</svg></div>'
        '<span style="font-size:1.4rem;font-weight:700;color:#071D35;letter-spacing:-0.02em">'
        'Invest<span style="font-weight:300;color:#1AB868">Wise</span></span>'
        '</div>'
        '<h2 style="color:#071D35;font-weight:800;font-size:1.45rem;margin:0 0 0.35rem">'
        'Welcome</h2>'
        '<p style="color:#5A8EBB;font-size:0.86rem;margin:0">'
        'Intelligence Hub &amp; News Feed are always free. '
        'All other modules require a free account.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Social OAuth buttons ──────────────────────────────────────────────────
    _render_social_buttons()

    # Hide the email section while a provider redirect is pending
    if "_oauth_redirect" not in st.session_state:
        st.markdown(
            '<div class="iw-or-divider">or continue with email</div>',
            unsafe_allow_html=True,
        )

        # ── Sign In / Sign Up tabs ────────────────────────────────────────────
        tab_in, tab_up = st.tabs(["Sign In", "Sign Up"])

        with tab_in:
            email_in = st.text_input(
                "Email", placeholder="you@example.com", key="signin_email",
            )
            pw_in = st.text_input(
                "Password", type="password", placeholder="••••••••", key="signin_pw",
            )
            if st.button("Sign In", type="primary", use_container_width=True,
                         key="signin_btn"):
                if email_in and pw_in:
                    mock_login(email_in)
                    st.success("Signed in! Loading your dashboard…")
                    st.rerun()
                else:
                    st.error("Please enter your email and password.")

        with tab_up:
            name_up  = st.text_input("Full Name", placeholder="Jane Smith", key="signup_name")
            email_up = st.text_input("Email", placeholder="you@example.com", key="signup_email")
            pw_up    = st.text_input(
                "Password", type="password", placeholder="min. 8 characters", key="signup_pw",
            )
            pw_up2   = st.text_input(
                "Confirm Password", type="password", placeholder="repeat password",
                key="signup_pw2",
            )
            if st.button(
                "Create Account", type="primary", use_container_width=True, key="signup_btn",
            ):
                if not email_up or not pw_up:
                    st.error("Email and password are required.")
                elif pw_up != pw_up2:
                    st.error("Passwords do not match.")
                elif len(pw_up) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    mock_login(email_up, name_up or "")
                    st.success("Account created! Welcome to InvestWise.")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # close iw-auth-wrap
