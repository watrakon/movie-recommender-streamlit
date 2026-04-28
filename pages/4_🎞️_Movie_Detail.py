import streamlit as st

from app import _get_lang, _localize_genres, _poster_url, _render_movie_card, apply_fx_theme, restore_auth
from services.api_client import ApiError, get_movie as api_get_movie, create_movie as api_create_movie
from services.api_client import list_movie_ratings as api_list_movie_ratings
from services.api_client import movie_ratings_summary as api_movie_ratings_summary
from services.api_client import list_user_ratings as api_list_user_ratings
from services.api_client import rate_movie as api_rate_movie
from services.api_client import recommend_hybrid as api_recommend_hybrid
from services.api_client import log_activity
from services.tmdb_client import fetch_movie_details_by_id_from_tmdb, fetch_movie_details_from_tmdb, fetch_movie_trailer_from_tmdb


from services.ui import render_sidebar_nav


st.set_page_config(page_title="Movie Detail", page_icon="🎞️", layout="wide")


def main():
    from services.ui import render_heartbeat
    render_sidebar_nav()
    # กู้สถานะล็อกอินจาก URL/Cookie เพื่อให้รู้ว่าผู้ใช้เป็นใคร (จำเป็นสำหรับการให้คะแนน)
    restore_auth()

    # Track Heartbeat
    current_user = st.session_state.get("current_user_id")
    movie_id = st.session_state.get("selected_movie_id")
    if current_user:
        render_heartbeat(current_user, movie_id=movie_id)

    # ใส่ธีม/เอฟเฟกต์ของทั้งเว็บให้เหมือนกันทุกหน้า
    apply_fx_theme()
    # อ่านภาษาที่ผู้ใช้เลือก (th/en)
    lang = _get_lang()
    page_title = "รายละเอียดภาพยนตร์" if lang == "th" else "Movie Detail"
    st.title(page_title)

    # selected_movie_id จะถูกตั้งค่ามาจากหน้าอื่น (เช่นการ์ดหนัง/หน้ารวม)
    movie_id = st.session_state.get("selected_movie_id")
    # selected_tmdb_id ใช้เป็น fallback กรณีไม่ได้มีในฐานข้อมูลของเรา แต่มีใน TMDB
    tmdb_id = st.session_state.get("selected_tmdb_id")

    # Log view activity
    user_id = st.session_state.get("current_user_id")
    view_sig = f"view_{movie_id}_{tmdb_id}"
    if user_id and st.session_state.get("last_view_sig") != view_sig:
        st.session_state["last_view_sig"] = view_sig
        try:
            if movie_id:
                log_activity(user_id, "view_movie", movie_id=int(movie_id))
            elif tmdb_id:
                log_activity(user_id, "view_movie_tmdb", details=f"tmdb_id:{tmdb_id}")
        except Exception:
            pass

    # ดึงรายละเอียดหนังจาก backend หรือ TMDB
    movie = None
    is_tmdb_only = False

    if movie_id:
        try:
            movie = api_get_movie(int(movie_id))
        except ApiError as exc:
            st.error(str(exc))
            if st.button("กลับหน้าแรก" if lang == "th" else "Back to home"):
                st.switch_page("app.py")
            return
    elif tmdb_id:
        try:
            details = fetch_movie_details_by_id_from_tmdb(int(tmdb_id), lang=lang)
            if isinstance(details, dict):
                # จำลองโครงสร้างให้เหมือน movie object จาก backend
                movie = {
                    "id": None, # ยังไม่มีใน DB
                    "tmdb_id": int(tmdb_id),
                    "title": details.get("title") or "",
                    "title_th": details.get("title") if lang == "th" else "",
                    "genres": "|".join(details.get("genres", [])),
                    "description": details.get("overview") or "",
                    "description_th": details.get("overview") if lang == "th" else "",
                    "poster_url": details.get("poster_url") or "",
                }
                is_tmdb_only = True
        except Exception:
            movie = None

    if not movie:
        st.info("ไม่พบข้อมูลภาพยนตร์" if lang == "th" else "Movie not found")
        if st.button("กลับหน้าแรก" if lang == "th" else "Back to home"):
            st.switch_page("app.py")
        return

    title = movie.get("title") or ""
    display_title = title
    if lang == "th":
        th = (movie.get("title_th") or "").strip()
        if th:
            display_title = th
    poster = _poster_url(
        {
            "title": display_title,
            "posterUrl": movie.get("poster_url") or "",
        }
    )

    # ลองดึงรายละเอียดเพิ่มเติมจาก TMDB (เช่น director/cast/runtime) เพื่อให้หน้า detail ดูครบขึ้น
    tmdb_details = None
    try:
        if title:
            tmdb_details = fetch_movie_details_from_tmdb(title=title, lang=lang)
    except Exception:
        tmdb_details = None

    year = ""
    runtime_str = ""
    director = ""
    cast_text = ""
    
    if isinstance(tmdb_details, dict):
        y = tmdb_details.get("release_year")
        r = tmdb_details.get("runtime_minutes")
        d = tmdb_details.get("director")
        c = tmdb_details.get("cast") or []
        
        if y: year = str(y)
        if r: runtime_str = f"{int(r)} นาที" if lang == "th" else f"{int(r)} min"
        if d: director = d
        if c: cast_text = ", ".join([str(x) for x in c if x])

    desc = ""
    if lang == "th":
        desc = (movie.get("description_th") or "").strip()
    if not desc:
        desc = (movie.get("description") or "").strip()
    if not desc and isinstance(tmdb_details, dict):
        desc = (tmdb_details.get("overview") or "").strip()
    if not desc:
        desc = "ไม่มีคำอธิบาย" if lang == "th" else "No description"
        
    genres = movie.get("genres") or ""
    display_genres = _localize_genres(genres) if lang == "th" else genres

    # Hero Banner HTML
    hero_html = f"""
    <div style="position: relative; border-radius: 20px; overflow: hidden; padding: 40px; background: rgba(11, 16, 32, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); margin-bottom: 2rem;">
        <div style="position: absolute; top: -20px; left: -20px; right: -20px; bottom: -20px; background-image: url('{poster}'); background-size: cover; background-position: center; filter: blur(40px) brightness(0.3); z-index: 0; opacity: 0.8;"></div>
        <div style="display: flex; gap: 40px; position: relative; z-index: 1; flex-wrap: wrap;">
            <div style="flex: 0 0 280px; border-radius: 16px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); overflow: hidden;">
                <img src="{poster}" style="width: 100%; display: block;" />
            </div>
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; min-width: 300px;">
                <h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 10px; background: linear-gradient(to right, #fff, rgba(255,255,255,0.7)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.2;">{display_title}</h1>
                <div style="color: rgba(34, 197, 94, 0.9); font-weight: 600; font-size: 1.1rem; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px;">{display_genres}</div>
                <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
                    {f'<div style="background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 8px; font-size: 0.9rem;">📅 {year}</div>' if year else ''}
                    {f'<div style="background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 8px; font-size: 0.9rem;">⏱️ {runtime_str}</div>' if runtime_str else ''}
                    {f'<div style="background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 8px; font-size: 0.9rem;">🎬 {director}</div>' if director else ''}
                </div>
                <p style="font-size: 1.05rem; line-height: 1.6; color: rgba(255,255,255,0.85); margin-bottom: 20px;">{desc}</p>
                {f'<div style="font-size: 0.9rem; color: rgba(255,255,255,0.5);"><strong>{"นักแสดง" if lang == "th" else "Cast"}:</strong> {cast_text}</div>' if cast_text else ''}
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

    # ดึงและแสดงตัวอย่างภาพยนตร์
    trailer_url = fetch_movie_trailer_from_tmdb(title) if title else None
    if trailer_url:
        st.markdown(f"### {'🎬 ตัวอย่างภาพยนตร์' if lang == 'th' else '🎬 Trailer'}")
        st.video(trailer_url)
        st.markdown("---")

    # ส่วนให้คะแนน: มีเฉพาะตอนผู้ใช้ล็อกอิน
    current_user = st.session_state.get("current_user_id")
    if current_user:
        target_id = movie.get("id")
        # โหลดเรทติ้งเดิมของผู้ใช้คนนี้ (ถ้าเคยให้คะแนนไว้) เพื่อ set ค่า default ใน UI
        existing_rating = None
        if target_id is not None:
            try:
                my_ratings = api_list_user_ratings(int(current_user))
                if isinstance(my_ratings, list):
                    for r in my_ratings:
                        if int(r.get("movie_id")) == int(target_id):
                            existing_rating = r.get("rating")
                            break
            except Exception:
                pass

        try:
            default_stars = int(round(float(existing_rating))) if existing_rating is not None else 0
        except Exception:
            default_stars = 0
        default_index = max(0, min(4, (default_stars - 1))) if default_stars else 3

        st.markdown(
            """
<style>
  div[data-testid="stRadio"] [role="radiogroup"] > label {
    padding: 6px 10px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.04);
    margin-right: 8px;
  }
  div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.16);
  }
  div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    border-color: rgba(34, 197, 94, 0.70) !important;
    background: rgba(34, 197, 94, 0.16) !important;
    box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.35) inset;
  }
  div[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {
    display: none !important;
  }
  div[data-testid="stRadio"] [role="radiogroup"] > label span {
    font-size: 18px;
    letter-spacing: 1px;
  }
  div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) span {
    color: rgb(187, 247, 208) !important;
  }
</style>
""",
            unsafe_allow_html=True,
        )

        # UI ให้คะแนนแบบดาว (1-5)
        stars = st.radio(
            "ให้คะแนนเรื่องนี้" if lang == "th" else "Rate this movie",
            options=[1, 2, 3, 4, 5],
            index=int(default_index),
            format_func=lambda v: "⭐" * int(v),
            horizontal=True,
        )
        # เมื่อกดบันทึก จะส่งคะแนนไป backend แล้ว rerun เพื่อให้ข้อมูลหน้าจออัปเดต
        if st.button("บันทึกคะแนน" if lang == "th" else "Save rating"):
            try:
                target_id = movie.get("id")
                if target_id is None:
                    # สร้างหนังใน DB ก่อน
                    payload = {
                        "tmdb_id": movie.get("tmdb_id"),
                        "title": movie.get("title"),
                        "title_th": movie.get("title_th"),
                        "genres": movie.get("genres"),
                        "description": movie.get("description"),
                        "description_th": movie.get("description_th"),
                        "poster_url": movie.get("poster_url"),
                    }
                    new_movie = api_create_movie(payload)
                    target_id = new_movie.get("id")
                    st.session_state["selected_movie_id"] = target_id
                    st.session_state.pop("selected_tmdb_id", None)

                api_rate_movie(int(current_user), int(target_id), float(int(stars)))
            except ApiError as exc:
                st.error(str(exc))
            else:
                st.success("บันทึกคะแนนเรียบร้อยแล้ว" if lang == "th" else "Rating saved")
                # ตั้ง flag เพื่อให้หลังบันทึกแล้วแสดงคำแนะนำ hybrid ใต้ส่วนให้คะแนนทันที
                st.session_state["detail_show_hybrid_recs"] = True
                # บังคับให้ดึงคำแนะนำใหม่ (กันกรณี cache ค่าเดิม)
                st.session_state["detail_hybrid_recs_signature"] = None
                st.rerun()

        # ถ้าผู้ใช้เพิ่งกดบันทึกคะแนน หรือเคยกดมาแล้ว ให้แสดงคำแนะนำ hybrid ใต้ส่วนให้คะแนน
        show_recs = bool(st.session_state.get("detail_show_hybrid_recs"))
        if show_recs:
            top_k = 10
            signature = f"{int(current_user)}|{int(movie_id)}|{int(top_k)}"
            # cache ผลลัพธ์คำแนะนำตาม signature เพื่อไม่เรียก API ซ้ำโดยไม่จำเป็น
            if st.session_state.get("detail_hybrid_recs_signature") != signature:
                st.session_state["detail_hybrid_recs_signature"] = signature
                try:
                    rec_movies = api_recommend_hybrid(int(current_user), top_k=int(top_k))
                except ApiError:
                    rec_movies = []
                st.session_state["detail_hybrid_recs_items"] = rec_movies

            rec_movies = st.session_state.get("detail_hybrid_recs_items") or []
            if rec_movies:
                st.markdown("---")
                st.subheader("✨ คำแนะนำสำหรับคุณ" if lang == "th" else "✨ Recommended for you")
                cols_per_row = 4
                for i in range(0, len(rec_movies), cols_per_row):
                    row = rec_movies[i : i + cols_per_row]
                    cols = st.columns(cols_per_row)
                    for col, m in zip(cols, row):
                        with col:
                            # แปลงรูปแบบจาก backend ให้เป็น format ที่ _render_movie_card ใช้
                            _render_movie_card(
                                {
                                    "movieId": m.get("id"),
                                    "title": m.get("title", ""),
                                    "genres": m.get("genres", "") or "",
                                    "description": m.get("description", "") or "",
                                    "posterUrl": m.get("poster_url", "") or "",
                                    "title_th": m.get("title_th", "") if isinstance(m, dict) else "",
                                    "description_th": m.get("description_th", "") if isinstance(m, dict) else "",
                                }
                            )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("กลับหน้าแรก" if lang == "th" else "Back to home"):
                st.switch_page("app.py")
        with c2:
            if st.button("ไปหน้า ⭐ ระบบแนะนำ" if lang == "th" else "Go to ⭐ Recommender"):
                st.switch_page("pages/3_⭐_Recommender.py")

    st.markdown("---")

    target_id = movie.get("id")
    if target_id is not None:
        try:
            summary = api_movie_ratings_summary(int(target_id))
        except ApiError:
            summary = {"count": 0, "average": 0.0}

        count = int(summary.get("count") or 0)
        avg = float(summary.get("average") or 0.0)

        m1, m2 = st.columns(2)
        m1.metric("จำนวนคนให้คะแนน" if lang == "th" else "Ratings count", count)
        m2.metric("คะแนนเฉลี่ย" if lang == "th" else "Average rating", f"{avg:.2f}")

        st.subheader("รายการคะแนน" if lang == "th" else "Ratings")
        try:
            ratings = api_list_movie_ratings(int(target_id), skip=0, limit=200)
        except ApiError:
            ratings = []

        if not ratings:
            st.info("ยังไม่มีใครให้คะแนนเรื่องนี้" if lang == "th" else "No ratings yet")
        else:
            rows = [
                {
                    ("ชื่อผู้ใช้" if lang == "th" else "username"): r.get("username"),
                    ("คะแนน" if lang == "th" else "rating"): r.get("rating"),
                    ("เวลา" if lang == "th" else "created_at"): r.get("created_at"),
                }
                for r in ratings
            ]
            st.dataframe(rows, use_container_width=True)
    else:
        st.info("ยังไม่มีคะแนนสำหรับภาพยนตร์เรื่องนี้ในระบบ (ดึงข้อมูลจาก TMDB)" if lang == "th" else "No ratings for this movie yet (data from TMDB)")


if __name__ == "__main__":
    main()
