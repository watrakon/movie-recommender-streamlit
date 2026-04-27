import hashlib
import hmac
import os
import re
from difflib import SequenceMatcher

import streamlit as st
from streamlit_cookies_manager import CookieManager

from config.settings import TMDB_API_KEY
from services.data_loader import load_movie_data, save_movie_data
from services.tmdb_client import fetch_movie_list_from_tmdb, fetch_poster_url_from_tmdb
from services.api_client import log_activity
from models.recommender import get_recommendations


st.set_page_config(
    page_title="Home - Movie Recommender",
    page_icon="🏠",
    layout="wide",
)


from services.ui import render_sidebar_nav, render_heartbeat

render_sidebar_nav()

user_id = st.session_state.get("current_user_id")
if user_id:
    render_heartbeat(user_id)

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Prompt:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', 'Prompt', sans-serif !important;
  }

  :root {
    --fx-bg-1: #060b14;
    --fx-bg-2: #051410;
    --fx-bg-3: #110820;
    --fx-accent: rgba(34, 197, 94, 0.85);
    --fx-accent-soft: rgba(34, 197, 94, 0.25);
  }
  .stApp {
    background: radial-gradient(1200px 800px at 12% 18%, rgba(34, 197, 94, 0.18), transparent 65%),
                radial-gradient(900px 600px at 86% 20%, rgba(168, 85, 247, 0.18), transparent 60%),
                radial-gradient(900px 700px at 40% 88%, rgba(59, 130, 246, 0.15), transparent 65%),
                linear-gradient(135deg, var(--fx-bg-1), var(--fx-bg-2));
  }
  .stApp::before {
    content: "";
    position: fixed;
    inset: -20vh -20vw;
    z-index: 0;
    pointer-events: none;
    background: linear-gradient(
      120deg,
      rgba(34, 197, 94, 0.15),
      rgba(59, 130, 246, 0.15),
      rgba(168, 85, 247, 0.15),
      rgba(34, 197, 94, 0.15)
    );
    filter: blur(28px);
    opacity: 0.45;
    transform: translate3d(0,0,0);
    animation: fxGlow 20s ease-in-out infinite;
  }
  @media (prefers-reduced-motion: reduce) {
    .stApp::before { animation: none !important; }
    section.main div[data-testid="stVerticalBlockBorderWrapper"] { transition: none !important; }
    section.main div[data-testid="stVerticalBlockBorderWrapper"] > div { transition: none !important; }
  }
  @keyframes fxGlow {
    0% { transform: translate3d(-2%, -1%, 0) rotate(0.0deg); }
    50% { transform: translate3d(1%, 0.5%, 0) rotate(0.25deg); }
    100% { transform: translate3d(-2%, -1%, 0) rotate(0.0deg); }
  }
  [data-testid="stAppViewContainer"],
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stSidebar"] {
    position: relative;
    z-index: 1;
  }
  [data-testid="stSidebarNav"] a {
    border-radius: 10px;
    padding: 8px 10px;
    margin: 2px 0;
  }
  [data-testid="stSidebarNav"] a:hover {
    background: rgba(255, 255, 255, 0.06);
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(34, 197, 94, 0.18);
    border: 1px solid rgba(34, 197, 94, 0.30);
  }

  div.stButton > button {
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.14);
    background:
      radial-gradient(500px 200px at 20% 15%, rgba(255,255,255,0.12), transparent 55%),
      linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.05));
    color: rgba(255,255,255,0.92);
    font-weight: 600;
    letter-spacing: 0.2px;
    transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
  }
  div.stButton > button {
    min-height: 42px;
  }
  div.stButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(34, 197, 94, 0.35);
    box-shadow: 0 12px 30px rgba(0,0,0,0.34);
    background:
      radial-gradient(500px 200px at 20% 15%, rgba(255,255,255,0.14), transparent 55%),
      linear-gradient(180deg, rgba(34,197,94,0.16), rgba(255,255,255,0.06));
  }
  div.stButton > button:active {
    transform: translateY(0px) scale(0.99);
  }
  div.stButton > button:focus-visible {
    outline: none;
    box-shadow:
      0 0 0 3px rgba(34, 197, 94, 0.22),
      0 12px 30px rgba(0,0,0,0.34);
  }
  div.stButton > button:disabled {
    opacity: 0.55;
    transform: none;
    box-shadow: none;
    border-color: rgba(255,255,255,0.10);
  }

  div.stButton > button[kind="secondary"] {
    background:
      radial-gradient(500px 200px at 20% 15%, rgba(255,255,255,0.10), transparent 55%),
      linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
  }

  div.stButton:has(button[data-testid="baseButton-secondary"][aria-label="movies_prev"]) > button,
  div.stButton:has(button[data-testid="baseButton-secondary"][aria-label="movies_next"]) > button {
    padding: 0.55rem 0.9rem;
  }

  div.stButton:has(button[aria-label="popular_preview_scroll_left"]) > button,
  div.stButton:has(button[aria-label="popular_preview_scroll_right"]) > button {
    width: 52px;
    height: 52px;
    border-radius: 999px;
    padding: 0;
    font-weight: 800;
  }

  .pager-status {
    min-height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    opacity: 0.88;
    font-weight: 600;
  }

  .fx-scroll-row {
    display: flex;
    gap: 14px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 10px 6px 14px 6px;
    scroll-snap-type: x proximity;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
    scrollbar-gutter: stable;
    scroll-padding-left: 6px;
    scroll-padding-right: 6px;
  }
  .fx-scroll-row-wrap {
    position: relative;
  }
  .fx-scroll-row-wrap::before,
  .fx-scroll-row-wrap::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    width: 56px;
    pointer-events: none;
    z-index: 2;
  }
  .fx-scroll-row-wrap::before {
    left: 0;
    background: linear-gradient(90deg, rgba(11,16,32,0.92), rgba(11,16,32,0));
  }
  .fx-scroll-row-wrap::after {
    right: 0;
    background: linear-gradient(270deg, rgba(11,16,32,0.92), rgba(11,16,32,0));
  }
  .fx-scroll-row::-webkit-scrollbar {
    height: 10px;
  }
  .fx-scroll-row::-webkit-scrollbar-track {
    background: rgba(255,255,255,0.05);
    border-radius: 999px;
  }
  .fx-scroll-row::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.14);
    border-radius: 999px;
  }
  .fx-scroll-row::-webkit-scrollbar-thumb:hover {
    background: rgba(34,197,94,0.28);
  }
  .fx-scroll-row {
    scrollbar-color: rgba(255,255,255,0.14) rgba(255,255,255,0.05);
    scrollbar-width: thin;
  }
  .fx-scroll-row:not(:hover)::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.08);
  }
  @media (prefers-reduced-motion: reduce) {
    .fx-scroll-row { scroll-behavior: auto; }
  }

  .fx-netflix-viewport {
    position: relative;
    overflow: hidden;
    padding: 10px 0 14px 0;
  }
  .fx-netflix-row {
    display: flex;
    gap: 14px;
    padding: 0 6px;
    will-change: transform;
    transition: transform 520ms cubic-bezier(.22,.61,.36,1);
  }
  @media (prefers-reduced-motion: reduce) {
    .fx-netflix-row { transition: none; }
  }
  .fx-scroll-card {
    flex: 0 0 auto;
    width: 170px;
    scroll-snap-align: start;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.03);
    overflow: hidden;
    transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
  }
  .fx-scroll-card:hover {
    transform: translateY(-3px) scale(1.02);
    border-color: rgba(34,197,94,0.28);
    box-shadow: 0 12px 26px rgba(0,0,0,0.32);
  }
  .fx-scroll-card img {
    display: block;
    width: 100%;
    aspect-ratio: 2 / 3;
    object-fit: cover;
  }
  .fx-scroll-card .fx-title {
    padding: 10px 10px 12px 10px;
    font-weight: 700;
    font-size: 0.90rem;
    line-height: 1.25;
    color: rgba(255,255,255,0.92);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 2.4em;
  }

  a.fx-poster-link {
    display: block;
    text-decoration: none;
    border-radius: 14px;
    overflow: hidden;
  }
  a.fx-poster-link img {
    display: block;
    width: 100%;
    height: auto;
    border-radius: 14px;
  }

  section.main div[data-testid="stVerticalBlockBorderWrapper"] {
    position: relative;
    transform: translateZ(0);
    transform-style: preserve-3d;
    will-change: transform;
    transition: transform 140ms ease;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] > div {
    position: relative;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    transition: box-shadow 160ms ease, border-color 160ms ease;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-3px) scale(1.01) !important;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"]:hover > div {
    border-color: rgba(34, 197, 94, 0.28);
    box-shadow:
      0 10px 28px rgba(0, 0, 0, 0.35),
      0 0 0 1px rgba(34, 197, 94, 0.14);
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"]::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 16px;
    pointer-events: none;
    opacity: 0;
    background: radial-gradient(600px 240px at 20% 15%, rgba(255,255,255,0.14), transparent 60%);
    transition: opacity 180ms ease;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"]:hover::after {
    opacity: 1;
  }

  /* Modern Input Fields */
  div[data-baseweb="input"] {
    border-radius: 12px !important;
    background-color: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    transition: all 150ms ease !important;
  }
  div[data-baseweb="input"]:focus-within {
    border-color: rgba(34, 197, 94, 0.5) !important;
    box-shadow: 0 0 12px rgba(34, 197, 94, 0.2) !important;
    background-color: rgba(255, 255, 255, 0.08) !important;
  }
  div[data-baseweb="input"] > div {
    background-color: transparent !important;
    border: none !important;
  }

  /* Custom Tab Styling */
  div[data-baseweb="tab-list"] {
    gap: 12px;
  }
  button[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
    transition: all 150ms ease !important;
  }
  button[data-baseweb="tab"]:hover {
    background: rgba(255, 255, 255, 0.05) !important;
  }
  button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(34, 197, 94, 0.15) !important;
    border-color: rgba(34, 197, 94, 0.3) !important;
  }
  div[data-baseweb="tab-highlight"] {
    display: none !important;
  }
  
  /* Google Link Button Styling */
  a.google-login-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    padding: 12px;
    text-decoration: none;
    color: white;
    font-weight: 600;
    transition: all 150ms ease;
  }
  a.google-login-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }
  a.google-login-btn img {
    width: 20px;
    height: 20px;
  }

  /* Glassmorphism Movie Cards */
  .fx-glass-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    overflow: hidden;
    transition: all 250ms ease;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  .fx-glass-card:hover {
    transform: translateY(-5px);
    border-color: rgba(34, 197, 94, 0.4);
    box-shadow: 0 15px 35px rgba(0,0,0,0.4), 0 0 20px rgba(34, 197, 94, 0.15);
  }
  .fx-glass-poster {
    width: 100%;
    aspect-ratio: 2 / 3;
    overflow: hidden;
  }
  .fx-glass-poster img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 300ms ease;
  }
  .fx-glass-card:hover .fx-glass-poster img {
    transform: scale(1.05);
  }
  .fx-glass-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
  }
  .fx-glass-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.95);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .fx-glass-genres {
    font-size: 0.8rem;
    color: rgba(34, 197, 94, 0.9);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .fx-glass-desc {
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.6);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

</style>
""",
    unsafe_allow_html=True,
)


def apply_fx_theme() -> None:
    st.markdown(
        """
<style>
  .stApp::before { display: none !important; }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] { transition: none !important; transform: none !important; }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] > div { transition: none !important; box-shadow: none !important; }
  section.main div[data-testid="stVerticalBlockBorderWrapper"]::after { display: none !important; }
</style>
""",
        unsafe_allow_html=True,
    )


@st.cache_data
def load_data():
    return load_movie_data()


@st.cache_data(ttl=600)
def _load_tmdb_popular(page: int, lang: str):
    return fetch_movie_list_from_tmdb(source="popular", page=int(page), lang=str(lang))


@st.cache_data(ttl=600)
def _tmdb_to_db_movie_id_map() -> dict:
    try:
        from services.api_client import list_movies as api_list_movies

        movies = api_list_movies(skip=0, limit=200000)
    except Exception:
        movies = []

    out = {}
    if isinstance(movies, list):
        for m in movies:
            if not isinstance(m, dict):
                continue
            db_id = m.get("id")
            tmdb_id = m.get("tmdb_id")
            try:
                if tmdb_id is not None and str(tmdb_id).strip() != "":
                    tid = int(tmdb_id)
                else:
                    continue
            except Exception:
                continue
            try:
                did = int(db_id)
            except Exception:
                continue
            out[tid] = did
    return out


def _get_lang() -> str:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "th"
    return st.session_state["lang"]


def _auth_secret() -> str:
    return os.getenv("AUTH_SECRET", "dev-secret-change-me")


_cookies = CookieManager(prefix="movie_recommender/")
if not _cookies.ready():
    st.stop()


def _sign_user_id(user_id: int) -> str:
    msg = str(int(user_id)).encode("utf-8")
    return hmac.new(_auth_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _qp_get(key: str) -> str:
    try:
        v = st.query_params.get(key)
        if isinstance(v, list):
            return str(v[0]) if v else ""
        return str(v) if v is not None else ""
    except Exception:
        qp = st.experimental_get_query_params()
        vals = qp.get(key) or []
        return str(vals[0]) if vals else ""


def _qp_set(**kwargs) -> None:
    try:
        for k, v in kwargs.items():
            if v is None:
                st.query_params.pop(k, None)
            else:
                st.query_params[k] = str(v)
    except Exception:
        qp = st.experimental_get_query_params()
        for k, v in kwargs.items():
            if v is None:
                qp.pop(k, None)
            else:
                qp[k] = [str(v)]
        st.experimental_set_query_params(**qp)


def set_auth_in_url(user_id: int) -> None:
    token = f"{int(user_id)}.{_sign_user_id(int(user_id))}"
    _qp_set(auth=token)


def set_auth_in_cookie(user_id: int) -> None:
    token = f"{int(user_id)}.{_sign_user_id(int(user_id))}"
    _cookies["auth"] = token
    _cookies.save()


def clear_auth_in_url() -> None:
    _qp_set(auth=None)


def clear_auth_in_cookie() -> None:
    _cookies["auth"] = ""
    _cookies.save()


def restore_auth_from_url() -> None:
    if st.session_state.get("current_user_id") is not None:
        return

    token = (_qp_get("auth") or "").strip()
    if not token or "." not in token:
        return

    user_part, sig_part = token.split(".", 1)
    try:
        user_id = int(user_part)
    except Exception:
        return

    expected = _sign_user_id(user_id)
    if not hmac.compare_digest(expected, sig_part):
        return

    st.session_state["current_user_id"] = user_id
    try:
        from services.api_client import get_user as api_get_user

        u = api_get_user(user_id)
        st.session_state["current_username"] = u.get("username") if isinstance(u, dict) else None
    except Exception:
        st.session_state["current_username"] = None


def restore_auth_from_cookie() -> None:
    if st.session_state.get("current_user_id") is not None:
        return

    token = str(_cookies.get("auth") or "").strip()
    if not token or "." not in token:
        return

    user_part, sig_part = token.split(".", 1)
    try:
        user_id = int(user_part)
    except Exception:
        return

    expected = _sign_user_id(user_id)
    if not hmac.compare_digest(expected, sig_part):
        return

    st.session_state["current_user_id"] = user_id
    try:
        from services.api_client import get_user as api_get_user

        u = api_get_user(user_id)
        st.session_state["current_username"] = u.get("username") if isinstance(u, dict) else None
    except Exception:
        st.session_state["current_username"] = None


def restore_auth() -> None:
    restore_auth_from_cookie()
    before = st.session_state.get("current_user_id")
    restore_auth_from_url()
    after = st.session_state.get("current_user_id")
    if before is None and after is not None:
        try:
            set_auth_in_cookie(int(after))
        except Exception:
            pass


def _t(key: str) -> str:
    lang = _get_lang()
    table = {
        "title": {"th": "🎬 Movie Recommender", "en": "🎬 Movie Recommender"},
        "subtitle": {
            "th": "ค้นหา แนะนำ และสำรวจภาพยนตร์ที่คุณอาจชอบ",
            "en": "Search, get recommendations and explore movies you may like",
        },
        "search_label": {"th": "🔍 ค้นหาชื่อหนังหรือคำอธิบาย", "en": "🔍 Search title or description"},
        "genre_filter": {"th": "กรองตามแนวภาพยนตร์", "en": "Filter by genre"},
        "recs_count": {"th": "จำนวนคำแนะนำ", "en": "Number of recommendations"},
        "no_movies": {
            "th": "ยังไม่มีข้อมูลภาพยนตร์ในไฟล์ `data/movies.csv` กรุณาเพิ่มข้อมูลก่อนใช้งานระบบแนะนำ",
            "en": "No movie data found in `data/movies.csv`. Please add some movies first.",
        },
        "no_results": {"th": "ไม่พบภาพยนตร์ที่ตรงกับเงื่อนไขค้นหา", "en": "No movies match your filters."},
        "list_header": {"th": "📚 รายการภาพยนตร์", "en": "📚 Movie list"},
        "recs_header": {"th": "✨ ระบบแนะนำภาพยนตร์", "en": "✨ Movie recommendations"},
        "pick_fav": {"th": "เลือกภาพยนตร์ที่คุณชอบ", "en": "Pick a movie you like"},
        "recs_button": {"th": "แนะนำภาพยนตร์จากเรื่องนี้", "en": "Recommend movies based on this"},
        "recs_for": {"th": "ผลการแนะนำสำหรับ", "en": "Recommendations for"},
        "recs_not_ready": {
            "th": "ยังไม่สามารถแนะนำภาพยนตร์ได้จากข้อมูลที่มี",
            "en": "Cannot generate recommendations with the current data.",
        },
    }
    return table.get(key, {}).get(lang, table.get(key, {}).get("en", key))


def _ensure_posters_auto(df_movies):
    """
    ดึงปกจาก TMDB อัตโนมัติเมื่อมีหนังที่ยังไม่มี posterUrl
    ทำแค่ครั้งแรกของ session เพื่อลดการยิง API ซ้ำ ๆ
    """
    if not TMDB_API_KEY:
        return df_movies

    if "posterUrl" not in df_movies.columns or df_movies.empty:
        return df_movies

    if st.session_state.get("auto_tmdb_poster_updated"):
        return df_movies

    # ถือว่าขาดปกเมื่อเป็น NaN หรือเป็นสตริงว่าง
    poster_col = df_movies["posterUrl"]
    missing_mask = poster_col.isna() | (poster_col.astype(str).str.strip() == "")
    if not missing_mask.any():
        st.session_state["auto_tmdb_poster_updated"] = True
        return df_movies

    # จำกัดจำนวนที่ดึงต่อรอบเพื่อไม่ให้ยิง API เยอะเกิน
    idxs = df_movies[missing_mask].head(10).index
    if len(idxs) == 0:
        st.session_state["auto_tmdb_poster_updated"] = True
        return df_movies

    with st.spinner(f"กำลังดึงปกจาก TMDB อัตโนมัติ {len(idxs)} เรื่อง..."):
        updated = 0
        for idx in idxs:
            title = df_movies.at[idx, "title"]
            poster = fetch_poster_url_from_tmdb(title)
            if poster:
                df_movies.at[idx, "posterUrl"] = poster
                updated += 1
        if updated:
            save_movie_data(df_movies)
        st.session_state["auto_tmdb_poster_updated"] = True

    return df_movies

def _poster_url(movie) -> str:
    """
    ใช้ URL ปกจาก TMDB ถ้ามีในคอลัมน์ posterUrl
    ถ้าไม่มีจะ fallback เป็น placeholder ที่อ่านง่าย
    """
    url = None
    if "posterUrl" in movie and isinstance(movie["posterUrl"], str) and movie["posterUrl"]:
        url = movie["posterUrl"]

    if url:
        return url

    text = str(movie["title"]).replace(" ", "+")
    return f"https://placehold.co/400x600/111111/FFFFFF?text={text}"


def _localize_genres(genres_str: str) -> str:
    """แปลงชื่อหมวดหมู่เป็นไทยเมื่อตั้งภาษาไทย แต่เก็บรูปแบบเดิมไว้ใช้กรอง"""
    if not isinstance(genres_str, str):
        return ""
    lang = _get_lang()
    if lang != "th":
        return genres_str
    mapping = {
        "Action": "แอ็กชัน",
        "Adventure": "ผจญภัย",
        "Animation": "แอนิเมชัน",
        "Comedy": "คอมเมดี้",
        "Crime": "อาชญากรรม",
        "Drama": "ดราม่า",
        "Fantasy": "แฟนตาซี",
        "Horror": "สยองขวัญ",
        "Mystery": "ลึกลับ",
        "Romance": "โรแมนติก",
        "Sci-Fi": "ไซไฟ",
        "Thriller": "ระทึกขวัญ",
    }
    parts = [p.strip() for p in genres_str.split("|") if p.strip()]
    localized = [mapping.get(p, p) for p in parts]
    return " | ".join(localized)


def _norm_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = re.sub(r"[\u200b\ufeff]", "", s)
    s = re.sub(r"[^0-9a-zA-Z\u0E00-\u0E7F\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _search_score(query: str, text: str) -> float:
    qn = _norm_text(query)
    tn = _norm_text(text)
    if not qn or not tn:
        return 0.0

    q_compact = qn.replace(" ", "")
    t_compact = tn.replace(" ", "")

    if tn == qn or t_compact == q_compact:
        return 1.0
    if tn.startswith(qn) or t_compact.startswith(q_compact):
        return 0.92
    if qn in tn or q_compact in t_compact:
        base = 0.82
    else:
        base = 0.0

    tokens = [t for t in qn.split(" ") if t]
    if tokens:
        hit = sum(1 for t in tokens if t in tn)
        coverage = hit / max(1, len(tokens))
    else:
        coverage = 0.0

    fuzzy = max(_fuzzy_ratio(qn, tn), _fuzzy_ratio(q_compact, t_compact))

    score = max(base, 0.55 * fuzzy + 0.35 * coverage)
    return float(score)

def _render_movie_card(movie, show_recommend_button: bool = False):
    poster = _poster_url(movie)
    movie_id = None
    try:
        movie_id = movie.get("movieId")
    except Exception:
        movie_id = None

    movie_id_str = ""
    if movie_id is not None:
        try:
            movie_id_str = str(movie_id).strip()
        except Exception:
            movie_id_str = ""
        if movie_id_str.lower() == "nan":
            movie_id_str = ""
            
    tmdb_id_str = ""
    tmdb_id = movie.get("tmdb_id")
    if tmdb_id is not None:
        try:
            tmdb_id_str = str(int(tmdb_id)).strip()
        except Exception:
            pass

    # html fallback text
    lang = _get_lang()
    display_title = movie.get("title_th") if lang == "th" and isinstance(movie.get("title_th"), str) and movie["title_th"] else movie["title"]
    
    genres = ""
    if isinstance(movie.get("genres"), str) and movie["genres"]:
        genres = _localize_genres(movie["genres"])
        
    desc_source = ""
    if lang == "th" and isinstance(movie.get("description_th"), str) and movie["description_th"]:
        desc_source = movie["description_th"]
    elif isinstance(movie.get("description"), str) and movie["description"]:
        desc_source = movie["description"]
        
    desc_trunc = desc_source[:160] + ("..." if len(desc_source) > 160 else "") if desc_source else ("ไม่มีคำอธิบาย" if lang == "th" else "No description")

    href = ""
    if movie_id_str:
        href = f"?open_movie_id={movie_id_str}"
    elif tmdb_id_str:
        href = f"?open_tmdb_id={tmdb_id_str}"
        
    card_html = f"""
    <a href="{href}" target="_self" style="text-decoration: none; color: inherit; display: block; height: 100%;">
        <div class="fx-glass-card">
            <div class="fx-glass-poster">
                <img src="{poster}" alt="Poster" />
            </div>
            <div class="fx-glass-content">
                <div class="fx-glass-title">{display_title}</div>
                <div class="fx-glass-genres">{genres}</div>
                <div class="fx-glass-desc">{desc_trunc}</div>
            </div>
        </div>
    </a>
    """
    
    # st.markdown adds its own paragraph wrapper, which can ruin height: 100%.
    st.markdown(card_html, unsafe_allow_html=True)

    if show_recommend_button:
        st.session_state["selected_title"] = movie["title"]


def main():
    restore_auth()
    apply_fx_theme()
    # Handle click-through from poster links
    try:
        open_movie_id = (st.query_params.get("open_movie_id") or "").strip()
    except Exception:
        open_movie_id = ""
    if open_movie_id:
        try:
            movie_id_int = int(float(open_movie_id))
            st.session_state["selected_movie_id"] = movie_id_int
            user_id = st.session_state.get("current_user_id")
            if user_id:
                try:
                    log_activity(user_id, "click_movie", movie_id=movie_id_int)
                except Exception:
                    pass
            _qp_set(open_movie_id=None)
            st.switch_page("pages/4_🎞️_Movie_Detail.py")
        except Exception:
            _qp_set(open_movie_id=None)

    # Handle click-through from Popular (TMDB) cards
    try:
        open_tmdb_id = (st.query_params.get("open_tmdb_id") or "").strip()
    except Exception:
        open_tmdb_id = ""
    if open_tmdb_id:
        try:
            tmdb_id = int(float(open_tmdb_id))
        except Exception:
            tmdb_id = None

        if tmdb_id:
            try:
                mapping = _tmdb_to_db_movie_id_map()
                db_movie_id = mapping.get(int(tmdb_id))
            except Exception:
                db_movie_id = None

            if db_movie_id:
                st.session_state.pop("selected_tmdb_id", None)
                st.session_state["selected_movie_id"] = int(db_movie_id)
                user_id = st.session_state.get("current_user_id")
                if user_id:
                    try:
                        log_activity(user_id, "click_popular_movie", movie_id=int(db_movie_id), details=f"tmdb_id:{tmdb_id}")
                    except Exception:
                        pass
            else:
                st.session_state.pop("selected_movie_id", None)
                st.session_state["selected_tmdb_id"] = int(tmdb_id)
                user_id = st.session_state.get("current_user_id")
                if user_id:
                    try:
                        log_activity(user_id, "click_popular_movie_tmdb", details=f"tmdb_id:{tmdb_id}")
                    except Exception:
                        pass

        _qp_set(open_tmdb_id=None)
        st.switch_page("pages/4_🎞️_Movie_Detail.py")
    # language toggle (sidebar) + login status
    with st.sidebar:
        lang = st.radio(
            "Language / ภาษา",
            options=["th", "en"],
            index=0 if _get_lang() == "th" else 1,
            format_func=lambda x: "ภาษาไทย" if x == "th" else "English",
        )
        st.session_state["lang"] = lang

        st.selectbox(
            "จำนวนต่อหน้า" if _get_lang() == "th" else "Items per page",
            options=[8, 12, 16, 24],
            index=1,
            key="movies_page_size",
        )

        # แสดงสถานะการเข้าสู่ระบบ
        current_user = st.session_state.get("current_user_id")
        if current_user:
            username = st.session_state.get("current_username") or f"User #{current_user}"
            st.success(f"เข้าสู่ระบบแล้ว: {username}" if lang == "th" else f"Logged in as: {username}")
            if st.button("ออกจากระบบ" if lang == "th" else "Log out"):
                st.session_state.pop("current_user_id", None)
                st.session_state.pop("current_username", None)
                clear_auth_in_url()
                clear_auth_in_cookie()
                st.rerun()
        else:
            st.warning(
                "กรุณาไปที่หน้า 🔐 Auth เพื่อเข้าสู่ระบบก่อนใช้งาน"
                if lang == "th"
                else "Please go to 🔐 Auth page to login first."
            )

    # ถ้ายังไม่ล็อกอิน ไม่ให้เข้าหน้าหลัก
    if "current_user_id" not in st.session_state:
        st.markdown(
            "### โปรดเข้าสู่ระบบก่อน\nไปที่เมนูด้านซ้ายและเลือกหน้า `🔐 Auth` เพื่อเข้าสู่ระบบ ก่อนใช้งานระบบแนะนำภาพยนตร์"
            if _get_lang() == "th"
            else "### Please log in first\nUse the `🔐 Auth` page from the left menu to log in before using the movie recommender."
        )
        return

    st.markdown(f"<h1 style='margin-bottom:0'>{_t('title')}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:gray;margin-top:0'>{_t('subtitle')}</p>",
        unsafe_allow_html=True,
    )

    df_movies = load_data()
    df_movies = _ensure_posters_auto(df_movies)

    if df_movies.empty:
        st.warning(_t("no_movies"))
        return

    # แถบค้นหา + ฟิลเตอร์ด้านบน
    with st.container():
        col_search, col_genre, col_num = st.columns([3, 2, 1])
        with col_search:
            query = st.text_input(_t("search_label"), "")
        with col_genre:
            raw_genres = sorted(
                {
                    g.strip()
                    for value in df_movies["genres"].dropna()
                    for g in str(value).split("|")
                    if g and g != "(no genres listed)"
                }
            )

            def _genre_label(g: str) -> str:
                # ใช้ฟังก์ชันเดียวกับบนการ์ด แต่ใส่ค่าทีละ genre
                return _localize_genres(g)

            selected_genre = st.selectbox(
                _t("genre_filter"),
                options=["ทั้งหมด"] + raw_genres,
                format_func=lambda g: "ทั้งหมด" if g == "ทั้งหมด" else _genre_label(g),
            )
        with col_num:
            n_recs = st.slider(_t("recs_count"), 5, 20, 10)

    # กรองข้อมูลตามการค้นหาและ genre
    df_filtered = df_movies.copy()
    if query:
        title_en = df_filtered.get("title", "").fillna("").astype(str)
        title_th = df_filtered.get("title_th", "").fillna("").astype(str)
        desc_en = df_filtered.get("description", "").fillna("").astype(str)
        desc_th = df_filtered.get("description_th", "").fillna("").astype(str)
        genres = df_filtered.get("genres", "").fillna("").astype(str)

        score_title = title_en.apply(lambda t: _search_score(query, t)).combine(
            title_th.apply(lambda t: _search_score(query, t)),
            max,
        )
        score_desc = desc_en.apply(lambda t: _search_score(query, t)).combine(
            desc_th.apply(lambda t: _search_score(query, t)),
            max,
        )
        score_genre = genres.apply(lambda t: _search_score(query, t))

        scores = (1.45 * score_title).combine(1.0 * score_desc, max).combine(0.75 * score_genre, max)
        df_filtered = df_filtered.assign(_search_score=scores)

        q_len = len(_norm_text(query).replace(" ", ""))
        min_score = 0.18 if q_len >= 3 else 0.12
        df_filtered = df_filtered[df_filtered["_search_score"] >= float(min_score)]
        df_filtered = df_filtered.sort_values(by="_search_score", ascending=False)
    if selected_genre != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["genres"].fillna("").str.contains(selected_genre)]

    # Pagination state
    if "movies_page" not in st.session_state:
        st.session_state["movies_page"] = 1

    filter_signature = f"{_get_lang()}|{query}|{selected_genre}"
    if st.session_state.get("movies_filter_signature") != filter_signature:
        st.session_state["movies_filter_signature"] = filter_signature
        st.session_state["movies_page"] = 1
        # Log search activity
        if query:
            user_id = st.session_state.get("current_user_id")
            if user_id:
                try:
                    log_activity(user_id, "search", query=query)
                except Exception:
                    pass

    page_size = int(st.session_state.get("movies_page_size") or 12)

    total_items = int(len(df_filtered))
    total_pages = max(1, (total_items + int(page_size) - 1) // int(page_size))
    st.session_state["movies_page"] = max(1, min(int(st.session_state["movies_page"]), total_pages))

    start = (int(st.session_state["movies_page"]) - 1) * int(page_size)
    end = start + int(page_size)
    df_page = df_filtered.iloc[start:end]

    st.markdown("---")

    if query and TMDB_API_KEY:
        st.subheader("🌐 ค้นหาจาก TMDB (ภาพยนตร์ทั่วโลก)" if _get_lang() == "th" else "🌐 TMDB Search Results")
        with st.spinner("กำลังค้นหาจาก TMDB..." if _get_lang() == "th" else "Searching TMDB..."):
            from services.tmdb_client import search_movies_from_tmdb
            tmdb_results = search_movies_from_tmdb(query, lang=_get_lang())
            
        if tmdb_results:
            cols_per_row = 4
            for i in range(0, len(tmdb_results), cols_per_row):
                row = tmdb_results[i : i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, m in zip(cols, row):
                    with col:
                        _render_movie_card({
                            "tmdb_id": m["tmdb_id"],
                            "title": m["title"],
                            "description": m["overview"],
                            "posterUrl": m["poster_url"]
                        })
        else:
            st.info("ไม่พบข้อมูลใน TMDB" if _get_lang() == "th" else "No results in TMDB")
        st.markdown("---")

    # Popular preview (top 10) shown immediately
    if TMDB_API_KEY and not _norm_text(str(query or "")):
        st.subheader("🔥 ยอดนิยม" if _get_lang() == "th" else "🔥 Popular")
        preview = _load_tmdb_popular(page=1, lang=_get_lang())[:10]
        if preview:
            if "popular_preview_start" not in st.session_state:
                st.session_state["popular_preview_start"] = 0

            window_size = 6
            max_start = max(0, len(preview) - window_size)
            start_idx = int(st.session_state.get("popular_preview_start") or 0)
            start_idx = max(0, min(start_idx, max_start))
            st.session_state["popular_preview_start"] = start_idx

            step_cards = 3

            card_w = 170
            gap = 14
            offset_px = int(start_idx) * int(card_w + gap)

            nav_l, nav_mid, nav_r = st.columns([1, 12, 1])
            with nav_l:
                if st.button("◀", key="popular_preview_scroll_left", disabled=start_idx <= 0, use_container_width=True):
                    st.session_state["popular_preview_start"] = max(0, start_idx - step_cards)
                    st.rerun()
            with nav_r:
                if st.button("▶", key="popular_preview_scroll_right", disabled=start_idx >= max_start, use_container_width=True):
                    st.session_state["popular_preview_start"] = min(max_start, start_idx + step_cards)
                    st.rerun()

            with nav_mid:
                cards_html = (
                    "<div class='fx-scroll-row-wrap'>"
                    "<div class='fx-netflix-viewport'>"
                    f"<div class='fx-netflix-row' style='transform: translate3d(-{offset_px}px,0,0)'>"
                )

                for m in preview:
                    title = str(m.get("title") or "")
                    title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    poster = str(m.get("poster_url") or "").strip()
                    tmdb_id = m.get("tmdb_id")
                    href = ""
                    try:
                        if tmdb_id is not None and str(tmdb_id).strip() != "":
                            href = f"?open_tmdb_id={int(tmdb_id)}"
                    except Exception:
                        href = ""

                    img_html = f"<img src='{poster}' alt='{title}'/>" if poster else ""
                    if href:
                        cards_html += (
                            f"<a class='card-link' href='{href}' target='_self'>"
                            f"<div class='fx-scroll-card'>{img_html}<div class='fx-title'>{title}</div></div>"
                            f"</a>"
                        )
                    else:
                        cards_html += f"<div class='fx-scroll-card'>{img_html}<div class='fx-title'>{title}</div></div>"

                cards_html += "</div></div></div>"
                st.markdown(cards_html, unsafe_allow_html=True)

            scol1, scol2, scol3 = st.columns([1, 1, 3])
            with scol1:
                if st.button(
                    "รีเฟรช" if _get_lang() == "th" else "Refresh",
                    key="popular_preview_refresh",
                ):
                    _load_tmdb_popular.clear()
                    st.rerun()

        st.markdown("---")

    # แสดงผลเป็นการ์ด
    if df_page.empty:
        st.info(_t("no_results"))
    else:
        st.subheader(_t("list_header"))
        cols_per_row = 4
        for i in range(0, len(df_page), cols_per_row):
            row = df_page.iloc[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, (_, movie) in zip(cols, row.iterrows()):
                with col:
                    _render_movie_card(movie)

        st.markdown("---")
        pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
        with pcol1:
            if st.button(
                "⬅️ ก่อนหน้า" if _get_lang() == "th" else "⬅️ Prev",
                disabled=st.session_state["movies_page"] <= 1,
                key="movies_prev",
                use_container_width=True,
            ):
                st.session_state["movies_page"] -= 1
                st.rerun()
        with pcol2:
            st.markdown(
                f"<div class='pager-status'>"
                f"{'หน้า' if _get_lang() == 'th' else 'Page'} {st.session_state['movies_page']} / {total_pages}"
                f" · {total_items} {'เรื่อง' if _get_lang() == 'th' else 'items'}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with pcol3:
            if st.button(
                "ถัดไป ➡️" if _get_lang() == "th" else "Next ➡️",
                disabled=st.session_state["movies_page"] >= total_pages,
                key="movies_next",
                use_container_width=True,
            ):
                st.session_state["movies_page"] += 1
                st.rerun()

if __name__ == "__main__":
    main()

