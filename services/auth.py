from __future__ import annotations

from typing import Optional, Tuple

from services.api_client import ApiError, login as api_login, signup as api_signup, get_user as api_get_user


def create_user(username: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    สมัครสมาชิกใหม่ (ฝั่ง Streamlit)

    หลักการ:
    - หน้านี้ทำหน้าที่เป็นตัวกลางเรียก backend ผ่าน services/api_client.py
    - คืนค่า (success, error_message) เพื่อให้หน้า UI แสดงผลได้ง่าย
    """
    username = username.strip()
    if not username or not password:
        return False, "Username และ Password ห้ามว่าง"

    try:
        api_signup(username=username, password=password)
    except ApiError as exc:
        return False, str(exc)
    return True, None


def authenticate(username: str, password: str) -> Optional[int]:
    """
    ตรวจสอบการเข้าสู่ระบบ

    การทำงาน:
    - เรียก backend /auth/login
    - ถ้าสำเร็จ backend จะคืน user object (มี id)
    - ฟังก์ชันนี้คืน userId ถ้าสำเร็จ, None ถ้าไม่สำเร็จ
    """
    username = username.strip()
    try:
        user = api_login(username=username, password=password)
    except ApiError:
        return None
    user_id = user.get("id")
    return int(user_id) if user_id is not None else None


def get_username(user_id: int) -> Optional[str]:
    # ดึง username จาก backend เพื่อใช้แสดงผลบนหน้าเว็บ
    try:
        user = api_get_user(int(user_id))
    except ApiError:
        return None
    username = user.get("username")
    return str(username) if username else None

