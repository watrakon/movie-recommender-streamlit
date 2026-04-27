from __future__ import annotations

import argparse
import time
from typing import Any, Dict, Tuple

from services.api_client import ApiError, list_movies, update_movie
from services.libretranslate_client import TranslateError, translate_text


def _needs_th(s: Any) -> bool:
    if s is None:
        return True
    if not isinstance(s, str):
        try:
            s = str(s)
        except Exception:
            return True
    return s.strip() == ""


def _is_probably_english(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    for ch in t:
        o = ord(ch)
        if 65 <= o <= 90 or 97 <= o <= 122:
            return True
    return False


def translate_missing_th(
    limit: int,
    sleep: float,
    only_if_english: bool,
) -> Tuple[int, int, int]:
    movies = list_movies(skip=0, limit=200000)

    translated = 0
    skipped = 0
    failed = 0

    cache: Dict[str, str] = {}

    for m in movies:
        if not isinstance(m, dict):
            skipped += 1
            continue

        movie_id = m.get("id")
        if movie_id is None:
            skipped += 1
            continue

        title = (m.get("title") or "").strip()
        desc = (m.get("description") or "").strip()

        title_th = m.get("title_th")
        desc_th = m.get("description_th")

        need_title = _needs_th(title_th)
        need_desc = _needs_th(desc_th)

        if only_if_english:
            if need_title and not _is_probably_english(title):
                need_title = False
            if need_desc and not _is_probably_english(desc):
                need_desc = False

        if not need_title and not need_desc:
            skipped += 1
            continue

        payload = {
            "tmdb_id": m.get("tmdb_id"),
            "title": m.get("title") or "",
            "genres": m.get("genres") or "",
            "description": m.get("description") or "",
            "poster_url": m.get("poster_url") or "",
            "title_th": (m.get("title_th") or ""),
            "description_th": (m.get("description_th") or ""),
        }

        try:
            if need_title and title:
                cache_key = f"t::{title}"
                if cache_key not in cache:
                    cache[cache_key] = translate_text(title, source="en", target="th")
                payload["title_th"] = cache[cache_key]

            if need_desc and desc:
                cache_key = f"d::{desc}"
                if cache_key not in cache:
                    cache[cache_key] = translate_text(desc, source="en", target="th")
                payload["description_th"] = cache[cache_key]

            update_movie(int(movie_id), payload)
            translated += 1

            if sleep:
                time.sleep(float(sleep))

            if limit and translated >= int(limit):
                break

        except (ApiError, TranslateError):
            failed += 1

    return translated, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--only-if-english", action="store_true")

    args = parser.parse_args()

    translated, skipped, failed = translate_missing_th(
        limit=int(args.limit),
        sleep=float(args.sleep),
        only_if_english=bool(args.only_if_english),
    )

    print(f"Translated={translated} Skipped={skipped} Failed={failed}")


if __name__ == "__main__":
    main()
