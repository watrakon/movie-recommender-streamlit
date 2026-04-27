from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class TranslateError(RuntimeError):
    # exception สำหรับงานแปลข้อความ
    pass


def _base_url() -> str:
    # URL ของบริการ LibreTranslate
    # สามารถตั้งค่า env `LIBRETRANSLATE_URL` เพื่อชี้ไปที่ server ของตัวเองได้
    return os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com").rstrip("/")


def translate_text(
    text: str,
    source: str = "en",
    target: str = "th",
    timeout: int = 20,
) -> str:
    # ฟังก์ชันแปลข้อความแบบง่าย
    # - รับข้อความภาษา source
    # - ส่งไปที่ LibreTranslate
    # - คืนค่าข้อความที่ถูกแปลเป็นภาษา target
    t = (text or "").strip()
    if not t:
        return ""

    url = f"{_base_url()}/translate"
    payload: Dict[str, Any] = {
        "q": t,
        "source": source,
        "target": target,
        "format": "text",
    }

    # เรียก API แปลภาษา
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except Exception as exc:
        raise TranslateError(f"Failed to call LibreTranslate: {exc}") from exc

    # ตรวจสอบ HTTP status
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        detail: Optional[str] = None
        try:
            data = resp.json()
            if isinstance(data, dict):
                detail = str(data.get("error") or data)
            else:
                detail = str(data)
        except Exception:
            detail = resp.text
        raise TranslateError(f"{resp.status_code} {resp.reason}: {detail}") from exc

    # แปลงผลลัพธ์เป็น JSON
    try:
        data = resp.json()
    except Exception as exc:
        raise TranslateError(f"Unexpected LibreTranslate response: {resp.text}") from exc

    if not isinstance(data, dict) or "translatedText" not in data:
        raise TranslateError(f"Unexpected LibreTranslate payload: {data}")

    # คืนข้อความที่แปลแล้ว
    return str(data.get("translatedText") or "")
