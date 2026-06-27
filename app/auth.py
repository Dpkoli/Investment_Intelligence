"""Authentication page and gate logic for InvestWise."""
from __future__ import annotations

import streamlit as st

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
    """Return a cached Supabase client, or None if unavailable."""
    try:
        from supabase import create_client  # lazy import — keeps startup crash-free
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None


def _get_oauth_url(provider: str) -> str | None:
    """Ask Supabase for an OAuth redirect URL without auto-opening a browser."""
    sb = _supabase()
    if sb is None:
        st.error(
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY "
            "to your Streamlit secrets.",
            icon="⚠️",
        )
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
    sb = _supabase()
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

_GOOGLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'style="display:inline-block;vertical-align:middle;flex-shrink:0">'
    '<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37'
    '-1.04 2.53-2.21 3.31v2.77h3.57C21.36 18.42 22.56 15.6 22.56 12.25z"/>'
    '<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06'
    '-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>'
    '<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07'
    'H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>'
    '<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97'
    ' 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>'
    '</svg>'
)

_GITHUB_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'fill="#24292e" style="display:inline-block;vertical-align:middle;flex-shrink:0">'
    '<path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261'
    '.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333'
    '-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834'
    ' 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467'
    '-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322'
    ' 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552'
    ' 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221'
    ' 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694'
    '.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>'
    '</svg>'
)

_AUTH_CSS = """<style>
/* ── Auth page page-level reset ─────────────────────────────────────── */
.iw-auth-wrap {
    max-width: 480px;
    margin: 0 auto;
    padding-bottom: 2rem;
}
/* Social buttons */
.iw-social-row {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
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
/* ── OAuth redirect panel ────────────────────────────────────────────── */
.iw-oauth-panel {
    background: #F8FAFD;
    border: 1.5px solid #D9E8F5;
    border-top: 3px solid #1AB868;
    border-radius: 10px;
    padding: 1.2rem 1.4rem 1rem;
    margin-bottom: 1rem;
    text-align: center;
}
.iw-oauth-panel-title {
    font-weight: 700;
    font-size: 0.95rem;
    color: #071D35;
    margin-bottom: 0.3rem;
}
.iw-oauth-panel-sub {
    font-size: 0.78rem;
    color: #5A8EBB;
    margin-bottom: 1rem;
}
/* Social icon+label display rows */
.iw-social-icon-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
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


def _render_social_buttons() -> None:
    """Render Google + GitHub OAuth buttons.

    Each button calls Supabase for a real OAuth URL and stores it in session
    state as ("provider", url).  A link_button is then shown to send the user
    to their chosen provider to complete the sign-in.
    """
    # If we already have a pending OAuth URL show the redirect panel instead
    if "_oauth_redirect" in st.session_state:
        provider, oauth_url = st.session_state["_oauth_redirect"]
        icon_svg  = _GOOGLE_SVG if provider == "google" else _GITHUB_SVG
        label     = "Google"    if provider == "google" else "GitHub"

        st.markdown(
            f'<div class="iw-oauth-panel">'
            f'<div class="iw-social-icon-row">{icon_svg}'
            f'<span class="iw-oauth-panel-title">Continue with {label}</span></div>'
            f'<p class="iw-oauth-panel-sub">'
            f'Click the button below to open the {label} sign-in page. '
            f"After you sign in you'll be returned here automatically.</p>"
            f'</div>',
            unsafe_allow_html=True,
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

    # Normal state: show Google + GitHub buttons side by side
    col_g, col_h = st.columns(2)

    with col_g:
        st.markdown(
            f'<div class="iw-social-icon-row">{_GOOGLE_SVG}'
            f'<span style="font-size:0.84rem;font-weight:600;color:#071D35">'
            f'Continue with Google</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Continue with Google", key="_oauth_google",
                     use_container_width=True):
            url = _get_oauth_url("google")
            if url:
                st.session_state["_oauth_redirect"] = ("google", url)
                st.rerun()

    with col_h:
        st.markdown(
            f'<div class="iw-social-icon-row">{_GITHUB_SVG}'
            f'<span style="font-size:0.84rem;font-weight:600;color:#071D35">'
            f'Continue with GitHub</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Continue with GitHub", key="_oauth_github",
                     use_container_width=True):
            url = _get_oauth_url("github")
            if url:
                st.session_state["_oauth_redirect"] = ("github", url)
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
        'Welcome back</h2>'
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
