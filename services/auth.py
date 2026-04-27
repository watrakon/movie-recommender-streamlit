from __future__ import annotations
import streamlit as st
from typing import Optional, Tuple
from services.api_client import ApiError, login as api_login, signup as api_signup, get_user as api_get_user

def create_user(username: str, password: str) -> Tuple[bool, Optional[str]]:
    username = username.strip()
    if not username or not password:
        return False, "Username และ Password ห้ามว่าง"
    try:
        api_signup(username=username, password=password)
    except ApiError as exc:
        return False, str(exc)
    return True, None

def authenticate(username: str, password: str) -> Optional[int]:
    username = username.strip()
    try:
        user = api_login(username=username, password=password)
    except ApiError:
        return None
    user_id = user.get("id")
    return int(user_id) if user_id is not None else None

def get_username(user_id: int) -> Optional[str]:
    try:
        user = api_get_user(int(user_id))
    except ApiError:
        return None
    return str(user.get("username")) if user else None

# Cookie and URL helpers for Auth
def clear_auth_in_cookie(user_id: int):
    # Placeholder for cookie management if needed
    pass

def clear_auth_in_url():
    st.query_params.clear()

def restore_auth():
    # Attempt to restore user_id from query params or session
    if "user_id" in st.query_params:
        return int(st.query_params["user_id"])
    return st.session_state.get("current_user_id")

def set_auth_in_cookie(user_id: int):
    # Placeholder
    pass

def set_auth_in_url(user_id: int):
    st.query_params["user_id"] = str(user_id)
