import streamlit as st

import os

from services.auth import authenticate, create_user, get_username
from app import _get_lang, apply_fx_theme
from app import clear_auth_in_cookie, clear_auth_in_url, restore_auth, set_auth_in_cookie, set_auth_in_url


from services.ui import render_sidebar_nav


st.set_page_config(page_title="Auth", page_icon="🔐", layout="centered")


def _set_current_user(user_id: int) -> None:
    st.session_state["current_user_id"] = int(user_id)
    st.session_state["current_username"] = get_username(int(user_id))
    set_auth_in_url(int(user_id))
    set_auth_in_cookie(int(user_id))


def main():
    render_sidebar_nav()
    restore_auth()
    apply_fx_theme()
    lang = _get_lang()
    st.title("🔐 Authentication" if lang == "en" else "🔐 ระบบสมาชิก")

    if "current_user_id" in st.session_state:
        st.success(
            f"Logged in as {st.session_state.get('current_username')}"
            if lang == "en"
            else f"เข้าสู่ระบบในชื่อ {st.session_state.get('current_username')}"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go to Home" if lang == "en" else "ไปหน้าแรก"):
                st.switch_page("app.py")
        with col2:
            if st.button("Log out" if lang == "en" else "ออกจากระบบ"):
                st.session_state.pop("current_user_id", None)
                st.session_state.pop("current_username", None)
                clear_auth_in_url()
                clear_auth_in_cookie()
                st.rerun()
        return

    tab_login, tab_signup = st.tabs(
        ["Login" if lang == "en" else "เข้าสู่ระบบ", "Sign up" if lang == "en" else "สมัครสมาชิก"]
    )

    with tab_login:
        st.markdown("<br>", unsafe_allow_html=True)
        
        api_base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        google_icon_url = "https://www.svgrepo.com/show/475656/google-color.svg"
        
        # Custom Google Button
        st.markdown(
            f"""
            <a href="{api_base}/auth/google/login" class="google-login-btn" style="display: flex; align-items: center; justify-content: center; gap: 10px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 12px; text-decoration: none; color: white; font-weight: 600; transition: all 150ms ease;" target="_self">
                <img src="{google_icon_url}" alt="Google Logo" style="width: 24px; height: 24px;" />
                {"Continue with Google" if lang == "en" else "เข้าสู่ระบบด้วย Google"}
            </a>
            <br>
            <div style="text-align: center; color: rgba(255,255,255,0.4); margin-bottom: 10px;">
                ──────── หรือเข้าสู่ระบบด้วยชื่อผู้ใช้ ────────
            </div>
            """,
            unsafe_allow_html=True
        )

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            user_id = authenticate(username, password)
            if user_id is None:
                st.error("Invalid username or password" if lang == "en" else "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            else:
                _set_current_user(user_id)
                st.success("Login successful" if lang == "en" else "เข้าสู่ระบบสำเร็จ")
                st.rerun()

    with tab_signup:
        st.markdown("<br>", unsafe_allow_html=True)
        new_username = st.text_input("Username", key="signup_username")
        new_password = st.text_input("Password", type="password", key="signup_password")
        new_password2 = st.text_input(
            "Confirm password" if lang == "en" else "ยืนยันรหัสผ่าน",
            type="password",
            key="signup_password2",
        )
        if st.button("Create account" if lang == "en" else "สร้างบัญชี"):
            if new_password != new_password2:
                st.error("Passwords do not match" if lang == "en" else "รหัสผ่านไม่ตรงกัน")
            else:
                ok, err = create_user(new_username, new_password)
                if not ok:
                    st.error(err or "Cannot create user")
                else:
                    st.success("Account created. Please login." if lang == "en" else "สร้างบัญชีสำเร็จ กรุณาเข้าสู่ระบบ")


if __name__ == "__main__":
    main()

