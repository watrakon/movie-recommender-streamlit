import pandas as pd

from services.api_client import ApiError, list_movies as api_list_movies
from services.api_client import list_ratings as api_list_ratings
from services.api_client import update_movie as api_update_movie


def load_movie_data() -> pd.DataFrame:
    # โหลดข้อมูลหนังจาก backend แล้วแปลงเป็น DataFrame สำหรับให้หน้า Streamlit ใช้งาน
    # จุดประสงค์คือทำให้ UI ฝั่ง Streamlit ไม่ต้องรู้รายละเอียด schema ของ backend มากนัก
    try:
        movies = api_list_movies(skip=0, limit=100000)
    except ApiError:
        movies = []

    # ถ้า backend คืนข้อมูลว่าง ให้สร้าง DataFrame เปล่า (มีคอลัมน์ขั้นต่ำ) เพื่อกัน error ในหน้า UI
    if not movies:
        df = pd.DataFrame(columns=["movieId", "title", "genres", "description", "posterUrl"])
    else:
        # แปลง key จาก backend (id, poster_url, description_th) ให้เป็นคีย์ที่หน้า UI ใช้
        df = pd.DataFrame(
            [
                {
                    "movieId": m.get("id"),
                    "title": m.get("title", ""),
                    "title_th": m.get("title_th", "") or "",
                    "genres": m.get("genres", "") or "",
                    "description": m.get("description", "") or "",
                    "description_th": m.get("description_th", "") or "",
                    "posterUrl": m.get("poster_url", "") or "",
                }
                for m in movies
            ]
        )

    # ตรวจสอบคอลัมน์ขั้นต่ำที่หน้า UI ต้องใช้ ถ้าขาดให้เติมค่าว่าง
    expected_cols = {"movieId", "title", "genres"}
    missing = expected_cols.difference(df.columns)
    if missing:
        for col in missing:
            df[col] = ""

    # ถ้าไม่มี description ให้ fallback จาก genres เพื่อให้โมเดล/หน้า UI ยังทำงานได้
    if "description" not in df.columns:
        df["description"] = df["genres"].fillna("")

    # ถ้าไม่มีปกหนัง ให้ตั้งเป็นค่าว่างไว้ก่อน
    if "posterUrl" not in df.columns:
        df["posterUrl"] = ""

    # รองรับฟิลด์ภาษาไทย (ถ้า backend ยังไม่มี จะเติมค่าว่าง)
    for col in ("title_th", "description_th"):
        if col not in df.columns:
            df[col] = ""

    return df


def save_movie_data(df: pd.DataFrame) -> None:
    # บันทึกข้อมูลหนังที่ถูกแก้ไขจากฝั่ง UI กลับไปที่ backend
    # (เช่น เพิ่ม title_th/description_th/แก้ posterUrl)
    for _, row in df.iterrows():
        movie_id = row.get("movieId")
        if movie_id is None or str(movie_id).strip() == "":
            continue

        payload = {
            "title": str(row.get("title", "")),
            "title_th": str(row.get("title_th", "") or ""),
            "genres": str(row.get("genres", "") or ""),
            "description": str(row.get("description", "") or ""),
            "description_th": str(row.get("description_th", "") or ""),
            "poster_url": str(row.get("posterUrl", "") or ""),
        }

        try:
            api_update_movie(int(movie_id), payload)
        except ApiError:
            continue


def load_ratings_data() -> pd.DataFrame:
    """โหลดข้อมูล rating ของผู้ใช้"""
    # โหลดเรทติ้งทั้งหมดจาก backend แล้วแปลงเป็น DataFrame
    # ใช้ในหน้าแนะนำ/หน้า detail เพื่อแสดงว่าผู้ใช้เคยให้คะแนนอะไรไปแล้ว
    try:
        ratings = api_list_ratings(skip=0, limit=200000)
    except Exception:
        ratings = []

    # ถ้าไม่มีข้อมูล ให้สร้าง DataFrame เปล่าเพื่อกัน error ใน UI
    if not ratings:
        df = pd.DataFrame(columns=["userId", "movieId", "rating", "timestamp"])
    else:
        # แปลง key จาก backend (user_id/movie_id/created_at) มาเป็นรูปแบบที่หน้า UI ใช้
        df = pd.DataFrame(
            [
                {
                    "userId": r.get("user_id"),
                    "movieId": r.get("movie_id"),
                    "rating": r.get("rating"),
                    "timestamp": r.get("created_at"),
                }
                for r in ratings
            ]
        )

    # เติมคอลัมน์ขั้นต่ำถ้าหาย
    for col in ("userId", "movieId", "rating"):
        if col not in df.columns:
            df[col] = 0
    return df

