from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class ApiError(RuntimeError):
    # Exception กลางสำหรับฝั่ง Streamlit เวลาคุยกับ backend แล้วได้ error
    pass


def _base_url() -> str:
    # URL หลักของ backend (FastAPI)
    # - ตอนรัน local ใช้ http://127.0.0.1:8000
    # - ตอน deploy ให้ตั้งค่า env `API_BASE_URL`
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _handle_response(resp: requests.Response) -> Any:
    # รวม logic การตรวจ status code + แปลง response เป็น JSON
    # ถ้า error จะโยน ApiError ที่อ่านง่ายออกไปให้หน้า UI แสดงผล
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        detail = None
        try:
            data = resp.json()
            detail = data.get("detail") if isinstance(data, dict) else data
        except Exception:
            detail = resp.text
        raise ApiError(f"{resp.status_code} {resp.reason}: {detail}") from exc

    if resp.status_code == 204:
        return None
    try:
        return resp.json()
    except Exception:
        return resp.text


def health() -> Dict[str, Any]:
    # health check เอาไว้เช็คว่า backend รันอยู่
    resp = requests.get(f"{_base_url()}/health", timeout=8)
    return _handle_response(resp)


def get_user(user_id: int) -> Dict[str, Any]:
    # ดึงข้อมูลผู้ใช้ตาม id
    resp = requests.get(f"{_base_url()}/users/{int(user_id)}", timeout=10)
    return _handle_response(resp)


def signup(username: str, password: str) -> Dict[str, Any]:
    # สมัครสมาชิกใหม่
    resp = requests.post(
        f"{_base_url()}/auth/signup",
        json={"username": username, "password": password},
        timeout=10,
    )
    return _handle_response(resp)


def login(username: str, password: str) -> Dict[str, Any]:
    # เข้าสู่ระบบ (backend จะคืน user object ถ้าสำเร็จ)
    resp = requests.post(
        f"{_base_url()}/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    return _handle_response(resp)


def list_movies(skip: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
    # ดึงรายการหนังทั้งหมดจาก backend
    resp = requests.get(f"{_base_url()}/movies", params={"skip": skip, "limit": limit}, timeout=15)
    data = _handle_response(resp)
    return data or []


def list_users(q: str = "", skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    # ค้นหา/แสดงรายชื่อผู้ใช้ (ใช้ในบางหน้า/บางฟีเจอร์)
    resp = requests.get(
        f"{_base_url()}/users",
        params={"q": q, "skip": skip, "limit": limit},
        timeout=15,
    )
    data = _handle_response(resp)
    return data or []


def list_ratings(skip: int = 0, limit: int = 200000) -> List[Dict[str, Any]]:
    # ดึงเรทติ้งทั้งหมด (ใช้ทำโมเดลแนะนำใน backend/บางหน้า)
    resp = requests.get(f"{_base_url()}/ratings", params={"skip": skip, "limit": limit}, timeout=20)
    data = _handle_response(resp)
    return data or []


def create_movie(payload: Dict[str, Any]) -> Dict[str, Any]:
    # เพิ่มหนังใหม่เข้า database
    resp = requests.post(f"{_base_url()}/movies", json=payload, timeout=15)
    return _handle_response(resp)


def update_movie(movie_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    # แก้ไขข้อมูลหนัง (เช่น title_th, description_th, poster_url)
    resp = requests.put(f"{_base_url()}/movies/{int(movie_id)}", json=payload, timeout=15)
    return _handle_response(resp)


def get_movie(movie_id: int) -> Dict[str, Any]:
    # ดึงรายละเอียดหนังจาก id
    resp = requests.get(f"{_base_url()}/movies/{int(movie_id)}", timeout=15)
    return _handle_response(resp)


def movie_ratings_summary(movie_id: int) -> Dict[str, Any]:
    # สรุปคะแนนของหนัง: จำนวนคนให้คะแนน + คะแนนเฉลี่ย
    resp = requests.get(f"{_base_url()}/movies/{int(movie_id)}/ratings-summary", timeout=15)
    return _handle_response(resp)


def list_movie_ratings(movie_id: int, skip: int = 0, limit: int = 200) -> List[Dict[str, Any]]:
    # ดึงรายการเรทติ้งของหนังเรื่องนั้น (ใครให้เท่าไร)
    resp = requests.get(
        f"{_base_url()}/movies/{int(movie_id)}/ratings",
        params={"skip": skip, "limit": limit},
        timeout=20,
    )
    data = _handle_response(resp)
    return data or []


def list_user_ratings(user_id: int) -> List[Dict[str, Any]]:
    # ดึงเรทติ้งทั้งหมดของผู้ใช้คนหนึ่ง
    resp = requests.get(f"{_base_url()}/users/{int(user_id)}/ratings", timeout=15)
    data = _handle_response(resp)
    return data or []


def rate_movie(user_id: int, movie_id: int, rating: float) -> Dict[str, Any]:
    # บันทึก/อัปเดตเรทติ้งของผู้ใช้ต่อหนังหนึ่งเรื่อง
    resp = requests.post(
        f"{_base_url()}/users/{int(user_id)}/ratings",
        json={"movie_id": int(movie_id), "rating": float(rating)},
        timeout=15,
    )
    return _handle_response(resp)


def recommend_by_movie(title: str, top_k: int = 10) -> List[Dict[str, Any]]:
    # แนะนำจากชื่อหนัง (content-based)
    resp = requests.get(
        f"{_base_url()}/recommend/by-movie",
        params={"title": title, "top_k": int(top_k)},
        timeout=30,
    )
    data = _handle_response(resp)
    return data or []


def recommend_by_user(user_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    # แนะนำจากพฤติกรรมผู้ใช้ (collaborative)
    resp = requests.get(
        f"{_base_url()}/recommend/by-user",
        params={"user_id": int(user_id), "top_k": int(top_k)},
        timeout=30,
    )
    data = _handle_response(resp)
    return data or []


def recommend_hybrid(user_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    # แนะนำแบบผสม (Hybrid) ซึ่ง backend จะรวม content-based + collaborative
    resp = requests.get(
        f"{_base_url()}/recommend/hybrid",
        params={"user_id": int(user_id), "top_k": int(top_k)},
        timeout=30,
    )
    data = _handle_response(resp)
    return data or []


def recommend_personal(user_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    # แนะนำแบบใช้ข้อมูลของผู้ใช้คนนั้นเป็นหลัก (personal-only)
    resp = requests.get(
        f"{_base_url()}/recommend/personal",
        params={"user_id": int(user_id), "top_k": int(top_k)},
        timeout=30,
    )
    data = _handle_response(resp)
    return data or []


def log_activity(
    user_id: int,
    activity_type: str,
    movie_id: Optional[int] = None,
    query: Optional[str] = None,
    details: Optional[str] = None,
) -> Dict[str, Any]:
    # บันทึกพฤติกรรมผู้ใช้
    payload = {
        "activity_type": activity_type,
        "movie_id": movie_id,
        "query": query,
        "details": details,
    }
    resp = requests.post(f"{_base_url()}/users/{int(user_id)}/activities", json=payload, timeout=10)
    return _handle_response(resp) or {}


def list_activities(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    resp = requests.get(f"{_base_url()}/activities", params={"skip": skip, "limit": limit}, timeout=15)
    return _handle_response(resp) or []


def get_behavior_stats() -> Dict[str, Any]:
    resp = requests.get(f"{_base_url()}/stats/behavior", timeout=15)
    return _handle_response(resp) or {}
