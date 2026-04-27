from __future__ import annotations

import hashlib
import hmac
import os
from urllib.parse import urlencode
from typing import Any
from typing import List

import pandas as pd
import requests
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from models.recommender import get_recommendations, recommend_for_user, recommend_for_user_mf

from . import crud, db, models, schemas


app = FastAPI(title="Movie Recommender API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


def _auth_secret() -> str:
    return os.getenv("AUTH_SECRET", "dev-secret-change-me")


def _sign_user_id(user_id: int) -> str:
    msg = str(int(user_id)).encode("utf-8")
    return hmac.new(_auth_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _frontend_base_url() -> str:
    # URL ของฝั่ง Streamlit สำหรับให้ backend redirect กลับหลัง login
    return os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8501").rstrip("/")


def _backend_base_url() -> str:
    # ใช้สร้าง redirect_uri ให้ Google callback กลับมาที่ backend
    # ค่าเดียวกับที่ Streamlit ใช้ยิง API อยู่แล้ว
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _google_client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "")


@app.get("/auth/google/login")
def google_login():
    client_id = _google_client_id()
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured")

    redirect_uri = f"{_backend_base_url()}/auth/google/callback"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth"
    return RedirectResponse(url=f"{url}?{urlencode(params)}")


@app.get("/auth/google/callback")
def google_callback(code: str = "", database: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    client_id = _google_client_id()
    client_secret = _google_client_secret()
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    redirect_uri = f"{_backend_base_url()}/auth/google/callback"
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    try:
        token_resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {token_resp.text}")

    payload = token_resp.json() if isinstance(token_resp.json(), dict) else {}
    raw_id_token = payload.get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=400, detail="Google did not return id_token")

    try:
        info = id_token.verify_oauth2_token(raw_id_token, google_requests.Request(), client_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Google id_token: {exc}")

    google_sub = str(info.get("sub") or "").strip()
    email = str(info.get("email") or "").strip()
    if not google_sub:
        raise HTTPException(status_code=400, detail="Google payload missing sub")

    user = crud.get_or_create_user_from_google(database, google_sub=google_sub, email=email)

    token = f"{int(user.id)}.{_sign_user_id(int(user.id))}"
    return RedirectResponse(url=f"{_frontend_base_url()}/?auth={token}")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/signup", response_model=schemas.User)
def signup(user_in: schemas.UserCreate, database: Session = Depends(get_db)):
    if crud.get_user_by_username(database, user_in.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    user = crud.create_user(database, user_in)
    return user


@app.post("/auth/login", response_model=schemas.User)
def login(payload: LoginRequest, database: Session = Depends(get_db)):
    user = crud.authenticate_user(database, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


@app.get("/users/{user_id}", response_model=schemas.User)
def get_user(user_id: int, database: Session = Depends(get_db)):
    user = crud.get_user(database, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users", response_model=List[schemas.User])
def list_users(q: str = "", skip: int = 0, limit: int = 100, database: Session = Depends(get_db)):
    return crud.search_users(database, q, skip=skip, limit=limit)


@app.get("/users/by-username/{username}", response_model=schemas.User)
def get_user_by_username(username: str, database: Session = Depends(get_db)):
    user = crud.get_user_by_username(database, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/movies", response_model=List[schemas.Movie])
def list_movies(skip: int = 0, limit: int = 100, database: Session = Depends(get_db)):
    return crud.list_movies(database, skip=skip, limit=limit)


@app.get("/movies/{movie_id}", response_model=schemas.Movie)
def get_movie(movie_id: int, database: Session = Depends(get_db)):
    movie = crud.get_movie(database, int(movie_id))
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.post("/movies", response_model=schemas.Movie, status_code=status.HTTP_201_CREATED)
def create_movie(movie_in: schemas.MovieCreate, database: Session = Depends(get_db)):
    return crud.create_movie(database, movie_in)


@app.put("/movies/{movie_id}", response_model=schemas.Movie)
def update_movie(movie_id: int, movie_in: schemas.MovieCreate, database: Session = Depends(get_db)):
    movie = crud.update_movie(database, int(movie_id), movie_in)
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.post("/users/{user_id}/ratings", response_model=schemas.Rating)
def rate_movie(user_id: int, rating_in: schemas.RatingCreate, database: Session = Depends(get_db)):
    user = database.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    movie = crud.get_movie(database, rating_in.movie_id)
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return crud.upsert_rating(database, user_id, rating_in)


@app.get("/users/{user_id}/ratings", response_model=List[schemas.Rating])
def get_user_ratings(user_id: int, database: Session = Depends(get_db)):
    return crud.list_ratings_for_user(database, user_id)


@app.post("/users/{user_id}/activities", response_model=schemas.UserActivity)
def log_user_activity(
    user_id: int, activity_in: schemas.UserActivityCreate, database: Session = Depends(get_db)
):
    user = crud.get_user(database, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return crud.create_user_activity(database, user_id, activity_in)


@app.get("/activities", response_model=List[schemas.UserActivity])
def list_activities(skip: int = 0, limit: int = 100, database: Session = Depends(get_db)):
    return crud.list_user_activities(database, skip=skip, limit=limit)


@app.get("/stats/behavior")
def get_behavior_stats(database: Session = Depends(get_db)):
    return crud.get_behavior_stats(database)


@app.get("/users/by-username/{username}/ratings", response_model=List[schemas.RatingWithMovie])
def get_ratings_by_username(username: str, database: Session = Depends(get_db)):
    user = crud.get_user_by_username(database, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    rows = (
        database.query(models.Rating, models.Movie)
        .join(models.Movie, models.Movie.id == models.Rating.movie_id)
        .filter(models.Rating.user_id == user.id)
        .order_by(models.Rating.created_at.desc())
        .all()
    )

    return [
        schemas.RatingWithMovie(
            user_id=user.id,
            username=user.username,
            movie_id=rating.movie_id,
            title=movie.title,
            rating=rating.rating,
            created_at=rating.created_at,
        )
        for rating, movie in rows
    ]


@app.get("/ratings", response_model=List[schemas.Rating])
def list_ratings(skip: int = 0, limit: int = 1000, database: Session = Depends(get_db)):
    return crud.list_ratings(database, skip=skip, limit=limit)


@app.get("/movies/{movie_id}/ratings", response_model=List[schemas.RatingWithUser])
def list_movie_ratings(movie_id: int, skip: int = 0, limit: int = 200, database: Session = Depends(get_db)):
    movie = crud.get_movie(database, int(movie_id))
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    rows = (
        database.query(models.Rating, models.User)
        .join(models.User, models.User.id == models.Rating.user_id)
        .filter(models.Rating.movie_id == int(movie_id))
        .order_by(models.Rating.created_at.desc())
        .offset(int(skip))
        .limit(int(limit))
        .all()
    )

    return [
        schemas.RatingWithUser(
            user_id=user.id,
            username=user.username,
            movie_id=rating.movie_id,
            rating=rating.rating,
            created_at=rating.created_at,
        )
        for rating, user in rows
    ]


@app.get("/movies/{movie_id}/ratings-summary", response_model=schemas.MovieRatingSummary)
def movie_ratings_summary(movie_id: int, database: Session = Depends(get_db)):
    movie = crud.get_movie(database, int(movie_id))
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    ratings = (
        database.query(models.Rating.rating)
        .filter(models.Rating.movie_id == int(movie_id))
        .all()
    )
    values = [float(r[0]) for r in ratings if r and r[0] is not None]
    count = len(values)
    avg = float(sum(values) / count) if count else 0.0
    return schemas.MovieRatingSummary(movie_id=int(movie_id), count=count, average=avg)


def _movies_df(database: Session) -> pd.DataFrame:
    movies = crud.list_movies(database, skip=0, limit=100000)
    if not movies:
        return pd.DataFrame(columns=["movieId", "title", "genres", "description", "posterUrl"])
    return pd.DataFrame(
        [
            {
                "movieId": m.id,
                "title": m.title,
                "title_th": getattr(m, "title_th", "") or "",
                "genres": m.genres or "",
                "description": m.description or "",
                "description_th": getattr(m, "description_th", "") or "",
                "posterUrl": m.poster_url or "",
            }
            for m in movies
        ]
    )


def _ratings_df(database: Session) -> pd.DataFrame:
    ratings = crud.list_ratings(database, skip=0, limit=200000)
    if not ratings:
        return pd.DataFrame(columns=["userId", "movieId", "rating", "timestamp"])
    return pd.DataFrame(
        [
            {
                "userId": r.user_id,
                "movieId": r.movie_id,
                "rating": r.rating,
                "timestamp": int(r.created_at.timestamp()) if r.created_at else 0,
            }
            for r in ratings
        ]
    )


@app.get("/recommend/by-movie", response_model=List[schemas.Movie])
def recommend_by_movie(title: str, top_k: int = 10, database: Session = Depends(get_db)):
    df_movies = _movies_df(database)
    if df_movies.empty:
        return []

    recs = get_recommendations(title, df_movies, top_k=int(top_k))
    if recs is None or recs.empty:
        return []

    titles = recs["title"].dropna().astype(str).tolist()
    if not titles:
        return []

    movies_by_title = {m.title: m for m in crud.list_movies(database, skip=0, limit=100000)}
    ordered: List[Any] = []
    for t in titles:
        m = movies_by_title.get(t)
        if m:
            ordered.append(m)
    return ordered


@app.get("/recommend/hybrid", response_model=List[schemas.Movie])
def recommend_hybrid(user_id: int, top_k: int = 10, database: Session = Depends(get_db)):
    df_movies = _movies_df(database)
    df_ratings = _ratings_df(database)
    if df_movies.empty or df_ratings.empty:
        return []

    top_k = int(top_k)
    user_id = int(user_id)

    movies_by_title = {m.title: m for m in crud.list_movies(database, skip=0, limit=100000)}

    try:
        cf_recs = recommend_for_user_mf(user_id, df_ratings, df_movies, top_k=max(20, top_k * 4))
    except Exception:
        cf_recs = recommend_for_user(user_id, df_ratings, df_movies, top_k=max(20, top_k * 4))
    cf_titles = []
    if isinstance(cf_recs, pd.DataFrame) and (not cf_recs.empty) and "title" in cf_recs.columns:
        cf_titles = cf_recs["title"].dropna().astype(str).tolist()

    user_r = df_ratings[df_ratings["userId"] == user_id]
    seed_titles = []
    if not user_r.empty:
        user_r = user_r.sort_values(by=["rating", "timestamp"], ascending=[False, False]).head(5)
        seed_ids = user_r["movieId"].dropna().astype(int).tolist()
        if seed_ids:
            seeds = df_movies[df_movies["movieId"].isin(seed_ids)][["movieId", "title"]]
            seed_titles = seeds["title"].dropna().astype(str).tolist()

    content_titles: list[str] = []
    if seed_titles:
        for t in seed_titles:
            try:
                recs = get_recommendations(t, df_movies, top_k=max(25, top_k * 4))
            except Exception:
                recs = None
            if isinstance(recs, pd.DataFrame) and (not recs.empty) and "title" in recs.columns:
                content_titles.extend(recs["title"].dropna().astype(str).tolist())

    scores: dict[str, float] = {}
    w_cf = 0.65
    w_cb = 0.35

    for i, t in enumerate(cf_titles):
        if not t:
            continue
        scores[t] = scores.get(t, 0.0) + float(w_cf) * (1.0 / float(i + 1))

    for i, t in enumerate(content_titles):
        if not t:
            continue
        scores[t] = scores.get(t, 0.0) + float(w_cb) * (1.0 / float(i + 1))

    seen_ids = set(user_r["movieId"].dropna().astype(int).tolist()) if not user_r.empty else set()
    ordered_titles = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True) if t]

    ordered: List[Any] = []
    for t in ordered_titles:
        m = movies_by_title.get(t)
        if not m:
            continue
        try:
            if int(m.id) in seen_ids:
                continue
        except Exception:
            pass
        ordered.append(m)
        if len(ordered) >= top_k:
            break
    return ordered


@app.get("/recommend/personal", response_model=List[schemas.Movie])
def recommend_personal(user_id: int, top_k: int = 10, database: Session = Depends(get_db)):
    df_movies = _movies_df(database)
    df_ratings = _ratings_df(database)
    if df_movies.empty or df_ratings.empty:
        return []

    top_k = int(top_k)
    user_id = int(user_id)

    user_r = df_ratings[df_ratings["userId"] == user_id]
    if user_r.empty:
        return []

    user_r = user_r.sort_values(by=["rating", "timestamp"], ascending=[False, False]).head(7)
    seed_ids = user_r["movieId"].dropna().astype(int).tolist()
    if not seed_ids:
        return []

    seed_rows = df_movies[df_movies["movieId"].isin(seed_ids)][["movieId", "title"]]
    seed_titles = seed_rows["title"].dropna().astype(str).tolist()
    if not seed_titles:
        return []

    seen_ids = set(df_ratings.loc[df_ratings["userId"] == user_id, "movieId"].dropna().astype(int).tolist())
    movies_by_title = {m.title: m for m in crud.list_movies(database, skip=0, limit=100000)}

    scores: dict[str, float] = {}
    for pos, t in enumerate(seed_titles):
        try:
            base_w = float(user_r.iloc[pos]["rating"]) / 5.0
        except Exception:
            base_w = 1.0

        try:
            recs = get_recommendations(t, df_movies, top_k=max(35, top_k * 6))
        except Exception:
            recs = None
        if not isinstance(recs, pd.DataFrame) or recs.empty or "title" not in recs.columns:
            continue
        titles = recs["title"].dropna().astype(str).tolist()
        for i, rt in enumerate(titles):
            if not rt:
                continue
            scores[rt] = scores.get(rt, 0.0) + base_w * (1.0 / float(i + 1))

    if not scores:
        return []

    ordered_titles = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True) if t]
    ordered: List[Any] = []
    for t in ordered_titles:
        m = movies_by_title.get(t)
        if not m:
            continue
        try:
            if int(m.id) in seen_ids:
                continue
        except Exception:
            pass
        ordered.append(m)
        if len(ordered) >= top_k:
            break
    return ordered


@app.get("/recommend/by-user", response_model=List[schemas.Movie])
def recommend_by_user(user_id: int, top_k: int = 10, database: Session = Depends(get_db)):
    df_movies = _movies_df(database)
    df_ratings = _ratings_df(database)
    if df_movies.empty or df_ratings.empty:
        return []

    recs = recommend_for_user(int(user_id), df_ratings, df_movies, top_k=int(top_k))
    if recs is None or recs.empty:
        return []

    titles = recs["title"].dropna().astype(str).tolist()
    movies_by_title = {m.title: m for m in crud.list_movies(database, skip=0, limit=100000)}
    ordered: List[Any] = []
    for t in titles:
        m = movies_by_title.get(t)
        if m:
            ordered.append(m)
    return ordered


# หมายเหตุ: endpoint แนะนำแบบ hybrid สามารถเรียกใช้โมเดล ML เดิมได้
# ในขั้นแรกเรายังไม่ผูกเข้ากับ ML เพื่อให้ backend โครงสร้างพร้อมก่อน

