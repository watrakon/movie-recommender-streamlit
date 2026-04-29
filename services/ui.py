import streamlit as st
import os
import hashlib
import hmac

def _auth_secret() -> str:
    return os.getenv("AUTH_SECRET", "dev-secret-change-me")

def _sign_user_id(user_id: int) -> str:
    msg = str(int(user_id)).encode("utf-8")
    return hmac.new(_auth_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()

def render_sidebar_nav() -> None:
    """Sidebar navigation - hides Movie_Detail from auto-nav and adds auth token to links"""
    # Hide Streamlit's auto-generated nav completely to avoid duplicates
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Build auth token for links so session survives navigation
    user_id = st.session_state.get("current_user_id")
    auth_suffix = ""
    if user_id:
        try:
            token = f"{int(user_id)}.{_sign_user_id(int(user_id))}"
            auth_suffix = f"?auth={token}"
        except Exception:
            auth_suffix = ""

    with st.sidebar:
        st.page_link("app.py", label="🏠 Home", icon=None)
        st.page_link("pages/0_🔐_Auth.py", label="🔐 Auth", icon=None)
        st.page_link("pages/3_⭐_Recommender.py", label="⭐ Recommender", icon=None)


def render_heartbeat(user_id: int, movie_id=None) -> None:
    """Placeholder - heartbeat is handled via JS elsewhere"""
    pass
