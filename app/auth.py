"""Authentication page and gate logic for InvestWise."""
from __future__ import annotations

import streamlit as st

_FREE_MODULES = {"Intelligence Hub", "News Feed"}


def check_auth() -> bool:
    return bool(st.session_state.get("is_authenticated", False))


def mock_login(email: str, display_name: str = "") -> None:
    st.session_state["is_authenticated"] = True
    st.session_state["user_email"] = email
    st.session_state["user_name"] = display_name or email.split("@")[0].title()


def logout() -> None:
    for k in ("is_authenticated", "user_email", "user_name", "_auth_tab"):
        st.session_state.pop(k, None)


def is_free_module(nav: str) -> bool:
    return nav in _FREE_MODULES


def render_auth_gate(module_name: str) -> None:
    """Show a paywall card when the user tries to access a gated module."""
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid #1AB868;'
        f'border-radius:10px;padding:2rem 1.5rem;max-width:480px;margin:3rem auto;text-align:center">'
        f'<div style="font-size:2rem;margin-bottom:0.5rem">🔒</div>'
        f'<h3 style="color:#071D35;font-weight:800;margin:0 0 0.4rem 0">{module_name}</h3>'
        f'<p style="color:#5A8EBB;font-size:0.88rem;margin:0 0 1.2rem 0">'
        f'Sign in to unlock this module and all premium features.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_auth_page(inline=True)


def render_auth_page(inline: bool = False) -> None:
    """Full sign-in / sign-up page."""
    if not inline:
        st.markdown(
            "<h2 class='iw-module-header'>Sign In to InvestWise</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="color:#5A8EBB;font-size:0.88rem;margin-bottom:1.25rem">'
            'Intelligence Hub and News Feed are free. All other modules require an account.</p>',
            unsafe_allow_html=True,
        )

    tab_in, tab_up = st.tabs(["Sign In", "Sign Up"])

    # ── Sign In ───────────────────────────────────────────────────────────────
    with tab_in:
        # OAuth buttons
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
            'margin:0.75rem 0">— or sign in with email —</div>',
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
                st.success("Signed in! Redirecting…")
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
            'margin:0.75rem 0">— or sign up with email —</div>',
            unsafe_allow_html=True,
        )

        name_up  = st.text_input("Full Name", placeholder="Jane Smith", key="signup_name")
        email_up = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        pw_up    = st.text_input("Password", type="password", placeholder="min. 8 chars", key="signup_pw")
        pw_up2   = st.text_input("Confirm Password", type="password", placeholder="repeat password", key="signup_pw2")

        if st.button("Create Account", type="primary", use_container_width=True, key="signup_btn"):
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
