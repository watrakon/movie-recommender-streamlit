from __future__ import annotations

import hashlib
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_google_sub(db: Session, google_sub: str) -> Optional[models.User]:
    sub = (google_sub or "").strip()
    if not sub:
        return None
    return db.query(models.User).filter(models.User.google_sub == sub).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    e = (email or "").strip().lower()
    if not e:
        return None
    return db.query(models.User).filter(models.User.email == e).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == int(user_id)).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def search_users(db: Session, query: str, skip: int = 0, limit: int = 100) -> List[models.User]:
    q = (query or "").strip()
    if not q:
        return list_users(db, skip=skip, limit=limit)
    return (
        db.query(models.User)
        .filter(models.User.username.ilike(f"%{q}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    user = models.User(username=user_in.username, password_hash=_hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_with_password_hash(db: Session, username: str, password_hash: str) -> models.User:
    user = models.User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_google_user(db: Session, username: str, google_sub: str, email: str) -> models.User:
    # สร้าง user สำหรับ Google OAuth โดยใส่ password_hash เป็นค่า placeholder
    # (ระบบนี้ใช้ token แบบ signed user_id ฝั่ง Streamlit อยู่แล้ว ไม่ได้ใช้ session ฝั่ง backend)
    placeholder_password_hash = _hash_password(google_sub or email or username)
    user = models.User(
        username=username,
        password_hash=placeholder_password_hash,
        google_sub=(google_sub or None),
        email=(email or None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user_from_google(db: Session, google_sub: str, email: str) -> models.User:
    # 1) หาโดย google_sub ก่อน (แม่นสุด)
    user = get_user_by_google_sub(db, google_sub)
    if user:
        # อัปเดต email ถ้ามีการเปลี่ยนแปลง
        if email and (user.email or "").lower() != email.lower():
            user.email = email
            db.commit()
            db.refresh(user)
        return user

    # 2) ถ้าไม่เจอ ให้ลองหาโดย email (เผื่อเคยสมัครด้วย username=email)
    by_email = get_user_by_email(db, email)
    if by_email:
        by_email.google_sub = google_sub
        db.commit()
        db.refresh(by_email)
        return by_email

    # 3) สร้างใหม่: ใช้ email เป็น username (ถ้าไม่มีให้ใช้ sub)
    base_username = ((email or "").strip() or f"google_{google_sub}").replace(" ", "")
    username = base_username
    # กันชนกรณีชื่อซ้ำ
    if get_user_by_username(db, username):
        suffix = (google_sub or "")[-6:] if google_sub else "new"
        username = f"{base_username}_{suffix}"

    return create_google_user(db, username=username, google_sub=google_sub, email=email)


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if user.password_hash != _hash_password(password):
        return None
    return user


def create_movie(db: Session, movie_in: schemas.MovieCreate) -> models.Movie:
    movie = models.Movie(
        tmdb_id=getattr(movie_in, "tmdb_id", None),
        title=movie_in.title,
        title_th=getattr(movie_in, "title_th", None) or "",
        genres=movie_in.genres or "",
        description=movie_in.description or "",
        description_th=getattr(movie_in, "description_th", None) or "",
        poster_url=movie_in.poster_url or "",
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


def list_movies(db: Session, skip: int = 0, limit: int = 100) -> List[models.Movie]:
    return db.query(models.Movie).offset(skip).limit(limit).all()


def get_movie(db: Session, movie_id: int) -> Optional[models.Movie]:
    return db.query(models.Movie).filter(models.Movie.id == movie_id).first()


def update_movie(db: Session, movie_id: int, movie_in: schemas.MovieCreate) -> Optional[models.Movie]:
    movie = get_movie(db, movie_id)
    if not movie:
        return None
    movie.tmdb_id = getattr(movie_in, "tmdb_id", None)
    movie.title = movie_in.title
    movie.title_th = getattr(movie_in, "title_th", None) or ""
    movie.genres = movie_in.genres or ""
    movie.description = movie_in.description or ""
    movie.description_th = getattr(movie_in, "description_th", None) or ""
    movie.poster_url = movie_in.poster_url or ""
    db.commit()
    db.refresh(movie)
    return movie


def upsert_rating(db: Session, user_id: int, rating_in: schemas.RatingCreate) -> models.Rating:
    rating = (
        db.query(models.Rating)
        .filter(models.Rating.user_id == user_id, models.Rating.movie_id == rating_in.movie_id)
        .first()
    )
    if rating:
        rating.rating = rating_in.rating
    else:
        rating = models.Rating(user_id=user_id, movie_id=rating_in.movie_id, rating=rating_in.rating)
        db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


def list_ratings_for_user(db: Session, user_id: int) -> List[models.Rating]:
    return db.query(models.Rating).filter(models.Rating.user_id == user_id).all()


def list_ratings(db: Session, skip: int = 0, limit: int = 1000) -> List[models.Rating]:
    return db.query(models.Rating).offset(skip).limit(limit).all()


def create_user_activity(
    db: Session, user_id: int, activity_in: schemas.UserActivityCreate
) -> models.UserActivity:
    activity = models.UserActivity(
        user_id=user_id,
        activity_type=activity_in.activity_type,
        movie_id=activity_in.movie_id,
        query=activity_in.query,
        details=activity_in.details,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def list_user_activities(db: Session, skip: int = 0, limit: int = 100) -> List[models.UserActivity]:
    return (
        db.query(models.UserActivity)
        .order_by(models.UserActivity.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_behavior_stats(db: Session) -> dict:
    from sqlalchemy import func
    
    total_activities = db.query(func.count(models.UserActivity.id)).scalar() or 0
    
    # Top searched queries
    top_queries = (
        db.query(models.UserActivity.query, func.count(models.UserActivity.id))
        .filter(models.UserActivity.activity_type == "search")
        .group_by(models.UserActivity.query)
        .order_by(func.count(models.UserActivity.id).desc())
        .limit(10)
        .all()
    )
    
    # Most viewed movies
    top_movies = (
        db.query(models.Movie.title, func.count(models.UserActivity.id))
        .join(models.UserActivity, models.Movie.id == models.UserActivity.movie_id)
        .filter(models.UserActivity.activity_type == "view_movie")
        .group_by(models.Movie.id)
        .order_by(func.count(models.UserActivity.id).desc())
        .limit(10)
        .all()
    )
    
    # Dwell time stats (Heartbeats)
    dwell_stats = (
        db.query(models.Movie.title, func.count(models.UserActivity.id))
        .join(models.UserActivity, models.Movie.id == models.UserActivity.movie_id)
        .filter(models.UserActivity.activity_type == "heartbeat")
        .group_by(models.Movie.id)
        .order_by(func.count(models.UserActivity.id).desc())
        .limit(10)
        .all()
    )
    
    return {
        "total_activities": total_activities,
        "top_queries": [{"query": q, "count": c} for q, c in top_queries],
        "top_movies": [{"title": t, "count": c} for t, c in top_movies],
        "dwell_stats": [{"title": t, "count": c, "seconds": c * 30} for t, c in dwell_stats],
    }

