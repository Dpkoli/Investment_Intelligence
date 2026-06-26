"""Authentication page and gate logic for InvestWise."""
from __future__ import annotations

import streamlit as st

_FREE_MODULES = {"Intelligence Hub", "News Feed"}

# Session-state key that signals "show the dedicated auth page"
_AUTH_PAGE_KEY = "_iw_show_auth_page"


def check_auth() -> bool:
    return bool(st.session_state.get("is_authenticated", False))


def mock_login(email: str, display_name: str = "") -> None:
    st.session_state["is_authenticated"] = True
    st.session_state["user_email"] = email
    st.session_state["user_name"] = display_name or email.split("@")[0].title()
    # Clear auth-page flag so the user lands back in the module they came from
    st.session_state.pop(_AUTH_PAGE_KEY, None)


def logout() -> None:
    for k in ("is_authenticated", "user_email", "user_name", _AUTH_PAGE_KEY):
        st.session_state.pop(k, None)


def is_free_module(nav: str) -> bool:
    return nav in _FREE_MODULES


def request_auth_page() -> None:
    """Navigate to the dedicated auth page (called by lock screens and sidebar)."""
    st.session_state[_AUTH_PAGE_KEY] = True
    st.rerun()


def wants_auth_page() -> bool:
    """True when the user should see the dedicated sign-in/sign-up page."""
    return bool(st.session_state.get(_AUTH_PAGE_KEY)) and not check_auth()


def render_auth_gate(module_name: str) -> None:
    """Clean lock-screen card with a single CTA that routes to the auth page."""
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;'
        f'border-top:3px solid #1AB868;border-radius:12px;'
        f'padding:2.5rem 2rem 2rem;max-width:460px;margin:4rem auto;text-align:center;'
        f'box-shadow:0 4px 20px rgba(7,29,53,0.08)">'
        f'<div style="font-size:2.4rem;margin-bottom:0.6rem">🔒</div>'
        f'<h3 style="color:#071D35;font-weight:800;font-size:1.15rem;'
        f'margin:0 0 0.5rem 0">{module_name}</h3>'
        f'<p style="color:#5A8EBB;font-size:0.88rem;margin:0 0 1.5rem 0;line-height:1.6">'
        f'This module requires an account. Sign in to unlock all premium intelligence '
        f'features — Intelligence Hub and News Feed are always free.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Centre the CTA button
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button(
            "Sign In / Create Account →",
            type="primary",
            use_container_width=True,
            key=f"_auth_gate_cta_{module_name.replace(' ', '_')}",
        ):
            request_auth_page()


def render_auth_page() -> None:
    """Dedicated full-page sign-in / sign-up form."""
    # Back link
    if st.button("← Back", key="_auth_back_btn"):
        st.session_state.pop(_AUTH_PAGE_KEY, None)
        st.rerun()

    st.markdown(
        "<h2 class='iw-module-header'>Sign In to InvestWise</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#5A8EBB;font-size:0.88rem;margin-bottom:1.5rem">'
        'Intelligence Hub and News Feed are always free. '
        'All other modules require a free account.</p>',
        unsafe_allow_html=True,
    )

    tab_in, tab_up = st.tabs(["Sign In", "Sign Up"])

    # ── Sign In ───────────────────────────────────────────────────────────────
    with tab_in:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "🔵  Continue with Google",
                use_container_width=True,
                key="auth_google_in",
            ):
                mock_login("user@gmail.com", "Google User")
                st.rerun()
        with c2:
            if st.button(
                "⚫  Continue with GitHub",
                use_container_width=True,
                key="auth_github_in",
            ):
                mock_login("user@github.com", "GitHub User")
                st.rerun()

        st.markdown(
            '<div style="text-align:center;color:#5A8EBB;font-size:0.78rem;'
            'margin:0.9rem 0">— or sign in with email —</div>',
            unsafe_allow_html=True,
        )

        email_in = st.text_input(
            "Email", placeholder="you@example.com", key="signin_email"
        )
        pw_in = st.text_input(
            "Password", type="password", placeholder="••••••••", key="signin_pw"
        )
        if st.button("Sign In", type="primary", use_container_width=True, key="signin_btn"):
            if email_in and pw_in:
                mock_login(email_in)
                st.success("Signed in! Loading your dashboard…")
                st.rerun()
            else:
                st.error("Please enter your email and password.")

    # ── Sign Up ───────────────────────────────────────────────────────────────
    with tab_up:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "🔵  Sign up with Google",
                use_container_width=True,
                key="auth_google_up",
            ):
                mock_login("newuser@gmail.com", "Google User")
                st.rerun()
        with c2:
            if st.button(
                "⚫  Sign up with GitHub",
                use_container_width=True,
                key="auth_github_up",
            ):
                mock_login("newuser@github.com", "GitHub User")
                st.rerun()

        st.markdown(
            '<div style="text-align:center;color:#5A8EBB;font-size:0.78rem;'
            'margin:0.9rem 0">— or sign up with email —</div>',
            unsafe_allow_html=True,
        )

        name_up  = st.text_input("Full Name", placeholder="Jane Smith", key="signup_name")
        email_up = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        pw_up    = st.text_input(
            "Password", type="password", placeholder="min. 8 characters", key="signup_pw"
        )
        pw_up2   = st.text_input(
            "Confirm Password", type="password", placeholder="repeat password", key="signup_pw2"
        )

        if st.button(
            "Create Account", type="primary", use_container_width=True, key="signup_btn"
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
