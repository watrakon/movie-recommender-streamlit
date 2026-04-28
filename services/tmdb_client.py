from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from config.settings import TMDB_API_KEY

logger = logging.getLogger(__name__)

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{movie_id}"
TMDB_MOVIE_CREDITS_URL = "https://api.themoviedb.org/3/movie/{movie_id}/credits"
TMDB_MOVIE_LIST_URL = "https://api.themoviedb.org/3/movie/{source}"
TMDB_VIDEO_URL = "https://api.themoviedb.org/3/movie/{movie_id}/videos"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _build_auth(key: str) -> Tuple[dict, dict]:
    """
    รองรับทั้ง v3 key (ค่า 32 ตัวเลข/ตัวอักษร) และ v4 token (เริ่มด้วย eyJ...)
    - ถ้าเป็น v4: ใช้ Authorization header
    - ถ้าเป็น v3: ใช้พารามิเตอร์ api_key
    """
    headers: dict = {}
    params: dict = {}

    if key.startswith("eyJ"):
        # v4 token
        headers["Authorization"] = f"Bearer {key}"
    else:
        # v3 api key
        params["api_key"] = key

    return headers, params


def fetch_poster_url_from_tmdb(title: str, api_key: Optional[str] = None) -> Optional[str]:
    """เรียก TMDB เพื่อดึง URL ปกหนัง ถ้าไม่พบจะคืน None"""
    # ฟังก์ชันนี้ใช้กรณีเรามีชื่อเรื่อง แต่ยังไม่มี poster_url ในฐานข้อมูล
    key = api_key or TMDB_API_KEY
    if not key:
        logger.warning("TMDB API key is not configured")
        return None

    headers, params = _build_auth(key)
    params.update({"query": title, "include_adult": "false"})

    try:
        resp = requests.get(
            TMDB_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=8,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Failed to call TMDB API for %s: %s", title, exc)
        return None

    data = resp.json()
    results = data.get("results") or []
    if not results:
        logger.info("TMDB returned no results for title %s", title)
        return None

    poster_path = results[0].get("poster_path")
    if not poster_path:
        return None

    return f"{TMDB_IMAGE_BASE}{poster_path}"

def fetch_movie_trailer_from_tmdb(title: str, api_key: Optional[str] = None) -> Optional[str]:
    """เรียก TMDB เพื่อหาตัวอย่างหนัง (YouTube) ถ้ามีจะคืน URL"""
    key = api_key or TMDB_API_KEY
    if not key: return None
    headers, params = _build_auth(key)
    
    # 1. ค้นหา TMDB movie_id จากชื่อเรื่อง
    search_params = params.copy()
    search_params.update({"query": title, "include_adult": "false"})
    try:
        resp = requests.get(TMDB_SEARCH_URL, params=search_params, headers=headers, timeout=8)
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if not results: return None
        tmdb_movie_id = results[0].get("id")
    except Exception as exc:
        logger.error("Failed to call TMDB API for %s: %s", title, exc)
        return None

    # 2. ดึงวิดีโอของภาพยนตร์
    try:
        url = TMDB_VIDEO_URL.format(movie_id=tmdb_movie_id)
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        videos = resp.json().get("results") or []
        for video in videos:
            if video.get("site") == "YouTube" and video.get("type") in ["Trailer", "Teaser"]:
                return f"https://www.youtube.com/watch?v={video.get('key')}"
    except Exception as exc:
        logger.error("Failed to fetch trailer for tmdb_id %s: %s", tmdb_movie_id, exc)
    return None


def _extract_title_year(raw_title: str) -> Tuple[str, Optional[int]]:
    # แยกปีท้ายชื่อเรื่องรูปแบบ "Movie Title (1999)" เพื่อช่วยให้ TMDB ค้นหาแม่นขึ้น
    if not isinstance(raw_title, str):
        return "", None
    raw_title = raw_title.strip()
    m = re.search(r"\((\d{4})\)\s*$", raw_title)
    if not m:
        return raw_title, None
    try:
        year = int(m.group(1))
    except Exception:
        year = None
    base = raw_title[: m.start()].strip()
    return base or raw_title, year


def _tmdb_language(lang: str) -> str:
    # map ภาษาในระบบ (th/en) ให้เป็นรหัส language ของ TMDB
    return "th-TH" if lang == "th" else "en-US"


def _tmdb_get(url: str, params: dict, headers: dict, timeout: int = 8) -> Optional[dict]:
    # helper กลางสำหรับเรียก TMDB แบบ GET พร้อม handle error/log
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to call TMDB API %s: %s", url, exc)
        return None


def fetch_movie_details_from_tmdb(
    title: str,
    lang: str = "en",
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    # ดึงรายละเอียดหนังจาก TMDB ด้วยชื่อเรื่อง
    # ใช้เพื่อเติมข้อมูลในหน้า Movie Detail (เช่น ผู้กำกับ นักแสดง ความยาว)
    key = api_key or TMDB_API_KEY
    if not key:
        logger.warning("TMDB API key is not configured")
        return None

    headers, base_params = _build_auth(key)
    query_title, year = _extract_title_year(title)
    params = dict(base_params)
    params.update(
        {
            "query": query_title,
            "include_adult": "false",
            "language": _tmdb_language(lang),
        }
    )
    if year:
        params["year"] = year

    # 1) ค้นหาเพื่อเอา tmdb_id ก่อน
    search = _tmdb_get(TMDB_SEARCH_URL, params=params, headers=headers)
    if not search:
        return None

    results = search.get("results") or []
    if not results:
        logger.info("TMDB returned no results for title %s", title)
        return None

    tmdb_id = results[0].get("id")
    if not tmdb_id:
        return None

    details_params = dict(base_params)
    details_params["language"] = _tmdb_language(lang)
    # 2) ดึงรายละเอียด + credits
    details = _tmdb_get(
        TMDB_MOVIE_URL.format(movie_id=tmdb_id),
        params=details_params,
        headers=headers,
    )
    credits = _tmdb_get(
        TMDB_MOVIE_CREDITS_URL.format(movie_id=tmdb_id),
        params=dict(base_params),
        headers=headers,
    )

    if not details:
        return None

    release_date = details.get("release_date") or ""
    release_year: Optional[int] = None
    if isinstance(release_date, str) and len(release_date) >= 4:
        try:
            release_year = int(release_date[:4])
        except Exception:
            release_year = None

    runtime = details.get("runtime")
    runtime_minutes: Optional[int] = None
    try:
        runtime_minutes = int(runtime) if runtime is not None else None
    except Exception:
        runtime_minutes = None

    director: Optional[str] = None
    cast_names: List[str] = []
    if isinstance(credits, dict):
        crew = credits.get("crew") or []
        if isinstance(crew, list):
            for c in crew:
                if isinstance(c, dict) and (c.get("job") == "Director"):
                    director = c.get("name")
                    break

        cast = credits.get("cast") or []
        if isinstance(cast, list):
            for c in cast[:8]:
                if isinstance(c, dict) and c.get("name"):
                    cast_names.append(str(c.get("name")))

    return {
        "tmdb_id": tmdb_id,
        "title": details.get("title"),
        "overview": details.get("overview"),
        "release_year": release_year,
        "runtime_minutes": runtime_minutes,
        "director": director,
        "cast": cast_names,
    }


def fetch_movie_details_by_id_from_tmdb(
    tmdb_id: int,
    lang: str = "en",
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    key = api_key or TMDB_API_KEY
    if not key:
        logger.warning("TMDB API key is not configured")
        return None

    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params["language"] = _tmdb_language(lang)

    details = _tmdb_get(
        TMDB_MOVIE_URL.format(movie_id=int(tmdb_id)),
        params=params,
        headers=headers,
        timeout=10,
    )
    if not isinstance(details, dict):
        return None

    poster_path = details.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if isinstance(poster_path, str) and poster_path else ""

    release_date = details.get("release_date") or ""
    release_year: Optional[int] = None
    if isinstance(release_date, str) and len(release_date) >= 4:
        try:
            release_year = int(release_date[:4])
        except Exception:
            release_year = None

    runtime = details.get("runtime")
    runtime_minutes: Optional[int] = None
    try:
        runtime_minutes = int(runtime) if runtime is not None else None
    except Exception:
        runtime_minutes = None

    return {
        "tmdb_id": int(tmdb_id),
        "title": details.get("title") or "",
        "overview": details.get("overview") or "",
        "release_year": release_year,
        "runtime_minutes": runtime_minutes,
        "poster_url": poster_url,
    }


def fetch_movie_list_from_tmdb(
    source: str,
    page: int = 1,
    lang: str = "en",
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # ดึง list หนังจาก TMDB (popular/top_rated/now_playing ฯลฯ) ตาม source
    # ใช้ตอน seed ข้อมูล หรือทำหน้า popular
    key = api_key or TMDB_API_KEY
    if not key:
        logger.warning("TMDB API key is not configured")
        return []

    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params.update({"page": int(page), "language": _tmdb_language(lang)})

    data = _tmdb_get(TMDB_MOVIE_LIST_URL.format(source=str(source)), params=params, headers=headers, timeout=10)
    if not isinstance(data, dict):
        return []

    results = data.get("results") or []
    if not isinstance(results, list):
        return []

    out: List[Dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        tmdb_id = item.get("id")
        if not isinstance(tmdb_id, int):
            continue
        poster_path = item.get("poster_path")
        poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if isinstance(poster_path, str) and poster_path else ""
        out.append(
            {
                "tmdb_id": tmdb_id,
                "title": item.get("title") or "",
                "overview": item.get("overview") or "",
                "release_date": item.get("release_date") or "",
                "poster_url": poster_url,
                "vote_average": item.get("vote_average"),
            }
        )
    return out


def search_movies_from_tmdb(
    query: str,
    page: int = 1,
    lang: str = "en",
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # ค้นหาภาพยนตร์จากชื่อเรื่องผ่าน TMDB
    key = api_key or TMDB_API_KEY
    if not key:
        logger.warning("TMDB API key is not configured")
        return []

    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params.update(
        {
            "query": query,
            "page": int(page),
            "language": _tmdb_language(lang),
            "include_adult": "false",
        }
    )

    data = _tmdb_get(TMDB_SEARCH_URL, params=params, headers=headers, timeout=10)
    if not isinstance(data, dict):
        return []

    results = data.get("results") or []
    if not isinstance(results, list):
        return []

    out: List[Dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        tmdb_id = item.get("id")
        if not isinstance(tmdb_id, int):
            continue
        poster_path = item.get("poster_path")
        poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if isinstance(poster_path, str) and poster_path else ""
        out.append(
            {
                "tmdb_id": tmdb_id,
                "title": item.get("title") or "",
                "overview": item.get("overview") or "",
                "release_date": item.get("release_date") or "",
                "poster_url": poster_url,
                "vote_average": item.get("vote_average"),
            }
        )
    return out
