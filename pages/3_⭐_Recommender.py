import streamlit as st

from services.data_loader import load_movie_data, load_ratings_data
from services.api_client import ApiError, recommend_hybrid as api_recommend_hybrid, log_activity
from app import _get_lang, _t, _render_movie_card, apply_fx_theme, restore_auth


from services.ui import render_sidebar_nav


st.set_page_config(page_title="Recommender", page_icon="⭐", layout="wide")


def main():
    render_sidebar_nav()
    # กู้สถานะล็อกอินจาก URL/Cookie (ถ้ามี) เพื่อให้ข้ามหน้าแล้วยังรู้ว่าเป็นผู้ใช้คนไหน
    restore_auth()
    # ใส่ธีม/เอฟเฟกต์ของทั้งเว็บ (พื้นหลัง/สี) ให้เหมือนกันทุกหน้า
    apply_fx_theme()
    # อ่านภาษาที่ผู้ใช้เลือก (th/en)
    lang = _get_lang()
    st.title("⭐ Movie Recommender" if lang == "en" else "⭐ ระบบแนะนำภาพยนตร์")
    st.caption(
        "Pick a movie you like or use your ratings to get personalized suggestions."
        if lang == "en"
        else "เลือกภาพยนตร์ที่คุณชอบ หรือใช้พฤติกรรมการให้คะแนนเพื่อรับคำแนะนำเฉพาะคุณ"
    )

    # โหลดข้อมูลหนัง/เรทติ้งจากฝั่ง service (โดยปกติจะดึงจาก backend แล้วแปลงเป็น DataFrame)
    df_movies = load_movie_data()
    df_ratings = load_ratings_data()
    # ถ้าไม่มีข้อมูลหนัง จะไม่สามารถแนะนำอะไรได้
    if df_movies.empty:
        msg = _t("no_movies") if hasattr(__import__("app"), "_t") else "No movie data."
        st.warning(msg)
        return

    # ดึงข้อมูลผู้ใช้ที่ล็อกอินอยู่จาก session_state
    current = st.session_state.get("current_user_id")
    current_name = st.session_state.get("current_username")

    # หน้าแนะนำนี้ออกแบบให้ “แนะนำสำหรับผู้ใช้ที่ล็อกอิน” เท่านั้น
    if not current:
        st.info(
            "กรุณาเข้าสู่ระบบก่อน เพื่อให้ระบบแนะนำจากคะแนนของคุณ"
            if lang == "th"
            else "Please log in first to get personalized recommendations."
        )
        return

    # user_id คือ id ที่จะส่งไป backend เพื่อคำนวณคำแนะนำ
    user_id = int(current)
    # นับจำนวนเรทติ้งของผู้ใช้นี้จาก backend โดยตรง (แม่นยำกว่าอ่านจาก DataFrame ที่อาจ cache เก่า)
    rating_count = 0
    try:
        from services.api_client import list_user_ratings as api_list_user_ratings
        my_ratings = api_list_user_ratings(user_id)
        rating_count = len(my_ratings) if isinstance(my_ratings, list) else 0
    except Exception:
        # fallback: นับจาก DataFrame ถ้า API ล้มเหลว
        try:
            rating_count = int((df_ratings["userId"] == int(user_id)).sum())
        except Exception:
            rating_count = 0

    # แสดงชื่อผู้ใช้ (ถ้ามี) เพื่อยืนยันว่าแนะนำสำหรับบัญชีนี้จริง
    label_name = current_name or f"User #{user_id}"
    st.caption(
        f"กำลังแนะนำสำหรับ: {label_name} (ให้คะแนนแล้ว {rating_count} รายการ)"
        if lang == "th"
        else f"Recommendations for: {label_name} ({rating_count} ratings)"
    )

    # ให้ผู้ใช้เลือกว่าอยากได้ผลลัพธ์กี่รายการ
    n_recs = st.slider(_t("recs_count"), 5, 20, 10)

    st.markdown("---")

    # signature ใช้กันการเรียก API ซ้ำทุกครั้งที่ Streamlit rerun
    # จะเรียกใหม่ก็ต่อเมื่อ user_id หรือจำนวนคำแนะนำเปลี่ยน
    signature = f"hybrid|{int(n_recs)}|{int(user_id)}"
    if st.session_state.get("recs_signature") != signature:
        st.session_state["recs_signature"] = signature
        try:
            # เรียก backend เพื่อขอคำแนะนำแบบผสม (Hybrid)
            rec_movies = api_recommend_hybrid(int(user_id), top_k=int(n_recs))
            # Log recommendation view
            try:
                log_activity(int(user_id), "view_recommendations", details=f"count:{n_recs},type:hybrid")
            except Exception:
                pass
        except ApiError:
            rec_movies = []
        st.session_state["recs_items"] = rec_movies

    # ดึงผลที่ cache ไว้มาแสดง (ถ้าไม่มีจะเป็น list ว่าง)
    rec_movies = st.session_state.get("recs_items") or []
    header = (
        f"คำแนะนำแบบผสม (Hybrid) สำหรับคุณ" if lang == "th" else "Hybrid recommendations for you"
    )

    if not rec_movies:
        st.info(_t("recs_not_ready"))
        return

    st.subheader(header)
    # แสดงผลลัพธ์เป็นการ์ด 4 ใบต่อแถว
    cols_per_row = 4
    for i in range(0, len(rec_movies), cols_per_row):
        row = rec_movies[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, movie in zip(cols, row):
            with col:
                m_id = movie.get("id")
                m_title = movie.get("title", "")
                m_title_th = movie.get("title_th", "") or ""
                m_poster = movie.get("poster_url", "") or ""
                m_genres = movie.get("genres", "") or ""
                m_desc = movie.get("description", "") or ""
                
                display_title = m_title_th if lang == "th" and m_title_th else m_title
                
                # แสดงโปสเตอร์
                if m_poster:
                    st.image(m_poster, use_container_width=True)
                else:
                    st.markdown(f"**{display_title}**")
                
                st.caption(display_title)
                
                # ปุ่มกดเข้าดูรายละเอียด
                btn_label = "ดูรายละเอียด" if lang == "th" else "View Details"
                if st.button(btn_label, key=f"rec_detail_{m_id}_{i}"):
                    st.session_state["selected_movie_id"] = m_id
                    st.session_state.pop("selected_tmdb_id", None)
                    try:
                        log_activity(user_id, "click_recommendation", movie_id=m_id, details="from:recommender_page")
                    except Exception:
                        pass
                    st.switch_page("pages/4_🎞️_Movie_Detail.py")


if __name__ == "__main__":
    main()

