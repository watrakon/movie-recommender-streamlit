from __future__ import annotations

import argparse
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from services.api_client import ApiError, create_movie, list_movies
from services.tmdb_client import TMDB_IMAGE_BASE, _build_auth


def _api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _get_tmdb_key(explicit_key: Optional[str]) -> str:
    key = explicit_key or os.getenv("TMDB_API_KEY", "").strip()
    if not key:
        raise RuntimeError("TMDB_API_KEY is not configured")
    return key


def _tmdb_get(url: str, headers: dict, params: dict, timeout: int = 12) -> dict:
    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected TMDB response")
    return data


def _tmdb_language(lang: str) -> str:
    return "th-TH" if lang == "th" else "en-US"


def _fetch_genre_map(key: str, lang: str) -> Dict[int, str]:
    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params["language"] = _tmdb_language(lang)
    data = _tmdb_get("https://api.themoviedb.org/3/genre/movie/list", headers=headers, params=params)
    genres = data.get("genres") or []
    out: Dict[int, str] = {}
    if isinstance(genres, list):
        for g in genres:
            if isinstance(g, dict) and isinstance(g.get("id"), int) and isinstance(g.get("name"), str):
                out[g["id"]] = g["name"].strip()
    return out


def _fetch_list_page(key: str, source: str, page: int, lang: str) -> List[Dict[str, Any]]:
    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params.update({"page": int(page), "language": _tmdb_language(lang)})
    url = f"https://api.themoviedb.org/3/movie/{source}"
    data = _tmdb_get(url, headers=headers, params=params)
    results = data.get("results") or []
    return results if isinstance(results, list) else []


def _fetch_movie_details(key: str, tmdb_id: int, lang: str) -> Dict[str, Any]:
    headers, base_params = _build_auth(key)
    params = dict(base_params)
    params["language"] = _tmdb_language(lang)
    url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
    return _tmdb_get(url, headers=headers, params=params)


def _safe_str(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def _year_from_date(d: Any) -> str:
    if not isinstance(d, str):
        return ""
    d = d.strip()
    if len(d) >= 4 and d[:4].isdigit():
        return d[:4]
    return ""


def _movie_key(title: str, year: str) -> str:
    t = (title or "").strip().lower()
    y = (year or "").strip()
    return f"{t}::{y}" if y else t


def _existing_movie_keys() -> set:
    existing = list_movies(skip=0, limit=200000)
    keys = set()
    for m in existing:
        if not isinstance(m, dict):
            continue
        title = _safe_str(m.get("title"))
        keys.add(_movie_key(title, ""))
    return keys


def _existing_tmdb_ids() -> set:
    existing = list_movies(skip=0, limit=200000)
    ids = set()
    for m in existing:
        if not isinstance(m, dict):
            continue
        tmdb_id = m.get("tmdb_id")
        if isinstance(tmdb_id, int):
            ids.add(tmdb_id)
        else:
            try:
                if tmdb_id is not None and str(tmdb_id).strip() != "":
                    ids.add(int(tmdb_id))
            except Exception:
                pass
    return ids


def import_from_tmdb(
    source: str,
    pages: int,
    delay: float,
    tmdb_key: Optional[str] = None,
    max_items: int = 0,
) -> Tuple[int, int]:
    key = _get_tmdb_key(tmdb_key)

    genre_map_en = _fetch_genre_map(key, "en")

    existing_keys = _existing_movie_keys()
    existing_tmdb_ids = _existing_tmdb_ids()

    imported = 0
    skipped = 0

    seen_tmdb_ids = set()

    for page in range(1, int(pages) + 1):
        items = _fetch_list_page(key=key, source=source, page=page, lang="en")
        for item in items:
            if not isinstance(item, dict):
                continue

            tmdb_id = item.get("id")
            if not isinstance(tmdb_id, int):
                continue
            if tmdb_id in seen_tmdb_ids:
                continue
            seen_tmdb_ids.add(tmdb_id)

            if tmdb_id in existing_tmdb_ids:
                skipped += 1
                continue

            details_en = _fetch_movie_details(key, tmdb_id, lang="en")
            details_th = _fetch_movie_details(key, tmdb_id, lang="th")

            title_en = _safe_str(details_en.get("title"))
            title_th = _safe_str(details_th.get("title"))
            release_year = _year_from_date(details_en.get("release_date"))

            if not title_en:
                skipped += 1
                continue

            key_title = _movie_key(title_en, "")
            if key_title in existing_keys:
                skipped += 1
                continue

            genre_ids = details_en.get("genre_ids")
            if not isinstance(genre_ids, list):
                genre_ids = item.get("genre_ids")
            genres = []
            if isinstance(genre_ids, list):
                for gid in genre_ids:
                    if isinstance(gid, int) and gid in genre_map_en:
                        genres.append(genre_map_en[gid])

            if not genres:
                genres_from_details = details_en.get("genres")
                if isinstance(genres_from_details, list):
                    for g in genres_from_details:
                        if isinstance(g, dict) and isinstance(g.get("name"), str):
                            genres.append(g["name"].strip())

            genres_str = " | ".join([g for g in genres if g])

            poster_path = details_en.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if isinstance(poster_path, str) and poster_path else ""

            overview_en = _safe_str(details_en.get("overview"))
            overview_th = _safe_str(details_th.get("overview"))

            if release_year:
                desc_en = f"{overview_en}"
                desc_th = f"{overview_th}"
            else:
                desc_en = overview_en
                desc_th = overview_th

            payload = {
                "tmdb_id": tmdb_id,
                "title": title_en,
                "title_th": title_th,
                "genres": genres_str,
                "description": desc_en,
                "description_th": desc_th,
                "poster_url": poster_url,
            }

            try:
                create_movie(payload)
                imported += 1
                existing_keys.add(key_title)
                existing_tmdb_ids.add(tmdb_id)
            except ApiError:
                skipped += 1

            if delay:
                time.sleep(float(delay))

            if max_items and imported >= int(max_items):
                return imported, skipped

    return imported, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="popular", choices=["popular", "top_rated", "now_playing", "upcoming"])
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--tmdb-key", default=None)

    args = parser.parse_args()

    print(f"API_BASE_URL={_api_base_url()}")
    imported, skipped = import_from_tmdb(
        source=str(args.source),
        pages=int(args.pages),
        delay=float(args.delay),
        tmdb_key=args.tmdb_key,
        max_items=int(args.max_items),
    )
    print(f"Imported={imported} Skipped={skipped}")


if __name__ == "__main__":
    main()
