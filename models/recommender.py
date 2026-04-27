from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity


def _build_content_model(movies: pd.DataFrame):
    # สร้างโมเดล content-based จากข้อความ description
    # 1) แปลง description -> TF-IDF vector
    # 2) คำนวณ cosine similarity ระหว่างหนังทุกคู่
    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(movies["description"].fillna(""))
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    indices = pd.Series(movies.index, index=movies["title"]).drop_duplicates()
    return cosine_sim, indices


def get_recommendations(title: str, movies: pd.DataFrame, top_k: int = 10) -> pd.DataFrame:
    """Content-based recommendation จากคำอธิบายหนัง"""
    # หลักการ: เลือกหนังตั้งต้น 1 เรื่อง แล้วคืนหนังที่มี description ใกล้เคียงที่สุด
    if movies.empty:
        return movies

    cosine_sim, indices = _build_content_model(movies)

    idx = indices.get(title)
    # ถ้าไม่เจอ title ใน index ให้ fallback ส่งรายการแรก ๆ ไปก่อน
    if idx is None:
        return movies.head(top_k)[["title", "genres"]]

    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1 : top_k + 1]
    movie_indices = [i[0] for i in sim_scores]
    return movies.iloc[movie_indices][["title", "genres"]]


def recommend_for_user(user_id: int, ratings: pd.DataFrame, movies: pd.DataFrame, top_k: int = 10) -> pd.DataFrame:
    """
    Collaborative filtering แบบง่าย (user-based):
    - ใช้ matrix user x movie จาก rating
    - หา users ที่มี pattern การให้คะแนนใกล้เคียง user เป้าหมาย
    - แนะนำหนังที่ user เป้าหมายยังไม่เคยดู แต่เพื่อนบ้านให้คะแนนสูง
    """
    if ratings.empty or movies.empty:
        return pd.DataFrame(columns=["title", "genres"])

    # เฉพาะ user ที่มี rating อย่างน้อย 1 รายการ
    if user_id not in ratings["userId"].unique():
        return pd.DataFrame(columns=["title", "genres"])

    user_item = ratings.pivot_table(index="userId", columns="movieId", values="rating")
    user_item_filled = user_item.fillna(0)

    # index ของ user ใน matrix
    if user_id not in user_item_filled.index:
        return pd.DataFrame(columns=["title", "genres"])

    # similarity ระหว่าง user เป้าหมายกับ user อื่น ๆ
    target_vector = user_item_filled.loc[[user_id]]
    sim_matrix = cosine_similarity(target_vector, user_item_filled)[0]
    sim_series = pd.Series(sim_matrix, index=user_item_filled.index)

    # ไม่รวมตัวเอง
    sim_series = sim_series.drop(user_id, errors="ignore")
    # top similar users
    similar_users = sim_series.sort_values(ascending=False).head(20)
    if similar_users.empty:
        return pd.DataFrame(columns=["title", "genres"])

    # คะแนนถ่วงน้ำหนักจากเพื่อนบ้าน
    neighbor_ratings = user_item.loc[similar_users.index]
    weighted_scores = neighbor_ratings.mul(similar_users, axis=0)
    score_sum = weighted_scores.sum(axis=0)
    sim_sum = (neighbor_ratings.notna().mul(similar_users, axis=0)).sum(axis=0)

    with pd.option_context("mode.use_inf_as_na", True):
        final_scores = score_sum / sim_sum.replace({0: pd.NA})

    # ตัดหนังที่ user นี้เคยให้คะแนนแล้ว
    seen_movie_ids = ratings.loc[ratings["userId"] == user_id, "movieId"].unique()
    final_scores = final_scores.drop(labels=seen_movie_ids, errors="ignore")

    final_scores = final_scores.dropna().sort_values(ascending=False).head(top_k)
    if final_scores.empty:
        return pd.DataFrame(columns=["title", "genres"])

    rec_movie_ids = final_scores.index.astype(int)
    rec_movies = movies[movies["movieId"].isin(rec_movie_ids)][["movieId", "title", "genres"]]

    # เรียงตามคะแนน
    rec_movies = rec_movies.set_index("movieId").loc[rec_movie_ids].reset_index()
    return rec_movies[["title", "genres"]]


def recommend_for_user_mf(
    user_id: int,
    ratings: pd.DataFrame,
    movies: pd.DataFrame,
    top_k: int = 10,
    n_components: int = 40,
    random_state: int = 42,
) -> pd.DataFrame:
    # Collaborative filtering แบบ Machine Learning (Matrix Factorization)
    # แนวคิด:
    # - สร้าง user-item matrix (rating)
    # - ทำ mean-centering ต่อผู้ใช้
    # - ใช้ TruncatedSVD หา latent factors
    # - คูณกลับเพื่อทำนายคะแนนของหนังที่ผู้ใช้ยังไม่เคยดู
    if ratings.empty or movies.empty:
        return pd.DataFrame(columns=["title", "genres"])

    if user_id not in ratings["userId"].unique():
        return pd.DataFrame(columns=["title", "genres"])

    user_item = ratings.pivot_table(index="userId", columns="movieId", values="rating")
    if user_item.empty or user_id not in user_item.index:
        return pd.DataFrame(columns=["title", "genres"])

    user_mean = user_item.mean(axis=1)
    # ลบค่าเฉลี่ยของแต่ละ user เพื่อให้โมเดลจับ "ความชอบ" ไม่ใช่ "สเกลการให้คะแนน" ของแต่ละคน
    centered = user_item.sub(user_mean, axis=0).fillna(0.0)

    n_users, n_items = centered.shape
    k = int(min(max(2, n_components), max(2, min(n_users - 1, n_items - 1))))
    if k < 2:
        return pd.DataFrame(columns=["title", "genres"])

    svd = TruncatedSVD(n_components=k, random_state=int(random_state))
    # user_factors: ตัวแทนผู้ใช้ใน latent space
    user_factors = svd.fit_transform(centered.values)
    # item_factors: ตัวแทนหนังใน latent space
    item_factors = svd.components_

    preds = np.dot(user_factors, item_factors) + user_mean.values.reshape(-1, 1)
    preds_df = pd.DataFrame(preds, index=centered.index, columns=centered.columns)

    user_preds = preds_df.loc[user_id].copy()
    # ตัดหนังที่ user เคยให้คะแนนแล้วออก
    seen_movie_ids = set(ratings.loc[ratings["userId"] == user_id, "movieId"].dropna().astype(int).tolist())
    user_preds = user_preds.drop(labels=list(seen_movie_ids), errors="ignore")
    user_preds = user_preds.dropna().sort_values(ascending=False).head(int(top_k))

    if user_preds.empty:
        return pd.DataFrame(columns=["title", "genres"])

    rec_movie_ids = user_preds.index.astype(int)
    rec_movies = movies[movies["movieId"].isin(rec_movie_ids)][["movieId", "title", "genres"]]
    if rec_movies.empty:
        return pd.DataFrame(columns=["title", "genres"])

    rec_movies = rec_movies.set_index("movieId").loc[rec_movie_ids].reset_index()
    return rec_movies[["title", "genres"]]

