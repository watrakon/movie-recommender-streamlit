import streamlit as st

from services.data_loader import load_movie_data, load_ratings_data
from services.auth import get_username
from services.api_client import ApiError, rate_movie as api_rate_movie
from app import _get_lang, _localize_genres, apply_fx_theme, restore_auth


st.set_page_config(page_title="Movie Explorer", page_icon="🎬", layout="wide")


def main():
    # หน้านี้ถูกปิดการใช้งานแล้ว (ซ่อนจากเมนู) และให้กลับไปหน้า Home แทน
    # หมายเหตุ: บางครั้ง Streamlit อาจยังเข้าถึงหน้านี้ได้จาก URL เดิม จึง redirect กันไว้
    try:
        st.switch_page("app.py")
    except Exception:
        pass

    restore_auth()
    apply_fx_theme()
    lang = _get_lang()
    st.title("🎬 Movie Explorer" if lang == "en" else "🎬 ค้นหาภาพยนตร์")
    df = load_movie_data()

    if df.empty:
        st.info("ยังไม่มีข้อมูลภาพยนตร์ใน `data/movies.csv`")
        return

    raw_genres = sorted(
        {
            g.strip()
            for value in df["genres"].dropna()
            for g in str(value).split("|")
            if g and g != "(no genres listed)"
        }
    )

    def _genre_label(g: str) -> str:
        return _localize_genres(g)

    selected_genre = st.selectbox(
        "เลือกแนวภาพยนตร์" if lang == "th" else "Select genre",
        options=["ทั้งหมด"] + raw_genres,
        format_func=lambda g: "ทั้งหมด"
        if g == "ทั้งหมด" and lang == "th"
        else ("All" if g == "ทั้งหมด" else _genre_label(g)),
    )

    if selected_genre != "ทั้งหมด":
        mask = df["genres"].fillna("").str.contains(selected_genre)
        df = df[mask]

    # ส่วนให้คะแนนภาพยนตร์ (ต้องล็อกอิน)
    st.markdown("---")
    st.subheader("ให้คะแนนภาพยนตร์ / Rate movies")
    current_user = st.session_state.get("current_user_id")
    if not current_user:
        st.info("เข้าสู่ระบบในหน้า 🔐 Auth ก่อนเพื่อให้คะแนนภาพยนตร์")
    else:
        username = get_username(int(current_user)) or current_user
        st.caption(f"กำลังให้คะแนนในนามผู้ใช้: {username}")
        df_ratings = load_ratings_data()

        col_movie, col_rating = st.columns([3, 1])
        with col_movie:
            # ใช้ชื่ออังกฤษเป็น key ภายใน
            titles = df["title"].tolist()
            movie_title = st.selectbox("เลือกรายการเพื่อให้คะแนน", options=titles)
        with col_rating:
            rating_value = st.slider("คะแนน (1-5)", 1, 5, 4)

        if st.button("บันทึกคะแนนนี้"):
            movie_id = int(df[df["title"] == movie_title]["movieId"].iloc[0])
            try:
                api_rate_movie(int(current_user), int(movie_id), float(rating_value))
            except ApiError as exc:
                st.error(str(exc))
            else:
                st.success("บันทึกคะแนนเรียบร้อยแล้ว")

    # แสดงชื่อเรื่องตามภาษา
    if lang == "th" and "title_th" in df.columns:
        df_display = df[["title_th", "genres"]].rename(columns={"title_th": "title"})
    else:
        df_display = df[["title", "genres"]]

    # แปลง genres เป็นภาษาไทยเพื่อแสดงผลถ้าเลือกภาษาไทย
    df_display = df_display.copy()
    df_display["genres"] = df_display["genres"].apply(_localize_genres)

    st.dataframe(df_display)


if __name__ == "__main__":
    main()

