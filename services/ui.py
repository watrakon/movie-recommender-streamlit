import streamlit as st
import re

def render_sidebar_nav():
    """Custom sidebar navigation styling"""
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                padding-top: 1rem;
            }
            [data-testid="stSidebarNav"] li:has(a[href*="Movie_Detail"]),
            [data-testid="stSidebarNav"] div:has(a[href*="Movie_Detail"]) {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

def render_heartbeat(user_id):
    """Placeholder for user heartbeat/activity"""
    pass

def apply_fx_theme():
    """Apply the Cyber-Cosmic theme globally"""
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Prompt:wght@300;400;500;600;700&display=swap');
      html, body, [class*="css"] { font-family: 'Inter', 'Prompt', sans-serif !important; }
      :root {
        --fx-bg-1: #060b14;
        --fx-bg-2: #051410;
        --fx-accent: rgba(34, 197, 94, 0.85);
      }
      .stApp {
        background: radial-gradient(1200px 800px at 12% 18%, rgba(34, 197, 94, 0.18), transparent 65%),
                    linear-gradient(135deg, var(--fx-bg-1), var(--fx-bg-2));
      }
    </style>
    """, unsafe_allow_html=True)

def _get_lang():
    """Get current language from session state"""
    return st.session_state.get("language", "th")

def _poster_url(movie):
    """Get poster URL with fallback"""
    poster = movie.get("posterUrl") or movie.get("poster_url")
    if not poster or str(poster).lower() == "nan":
        return "https://via.placeholder.com/500x750?text=No+Poster"
    return poster

def _localize_genres(genres_str):
    """Translate genres to Thai if needed"""
    if not genres_str: return ""
    translations = {
        "Action": "แอคชั่น", "Comedy": "ตลก", "Drama": "ดราม่า",
        "Sci-Fi": "ไซไฟ", "Horror": "สยองขวัญ", "Romance": "โรแมนติก"
    }
    for eng, th in translations.items():
        genres_str = genres_str.replace(eng, th)
    return genres_str
