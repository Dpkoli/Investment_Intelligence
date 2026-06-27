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


def _render_social_buttons() -> None:
    """Render Google + GitHub OAuth buttons using native st.button with icons."""
    # If a provider has already been selected show the redirect panel
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

    # Normal state: Google + GitHub side by side, single button each
    col_g, col_h = st.columns(2)

    with col_g:
        if st.button("Continue with Google", icon="🌐", key="_oauth_google",
                     use_container_width=True):
            url = _get_oauth_url("google")
            if url:
                st.session_state["_oauth_redirect"] = ("google", url)
                st.rerun()

    with col_h:
        if st.button("Continue with GitHub", icon="💻", key="_oauth_github",
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
