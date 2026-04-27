from __future__ import annotations

import pandas as pd

from backend import db, models


def _load_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()


def seed_from_csv() -> None:
    db.init_db()
    session = db.SessionLocal()
    try:
        df_movies = _load_csv("data/movies.csv")
        if not df_movies.empty:
            if "movieId" not in df_movies.columns:
                raise RuntimeError("movies.csv must contain movieId")

            for _, r in df_movies.iterrows():
                movie_id = int(r.get("movieId"))
                title = str(r.get("title") or "").strip()
                if not title:
                    continue

                m = models.Movie(
                    id=movie_id,
                    title=title,
                    title_th=str(r.get("title_th") or ""),
                    genres=str(r.get("genres") or ""),
                    description=str(r.get("description") or ""),
                    description_th=str(r.get("description_th") or ""),
                    poster_url=str(r.get("posterUrl") or ""),
                )
                session.merge(m)

        df_users = _load_csv("data/users.csv")
        if not df_users.empty:
            if "userId" not in df_users.columns:
                raise RuntimeError("users.csv must contain userId")

            for _, r in df_users.iterrows():
                user_id = int(r.get("userId"))
                username = str(r.get("username") or "").strip()
                password_hash = str(r.get("password_hash") or "").strip()
                if not username or not password_hash:
                    continue

                u = models.User(
                    id=user_id,
                    username=username,
                    password_hash=password_hash,
                )
                session.merge(u)

        df_ratings = _load_csv("data/ratings.csv")
        if not df_ratings.empty:
            required = {"userId", "movieId", "rating"}
            missing = required.difference(df_ratings.columns)
            if missing:
                raise RuntimeError(f"ratings.csv missing columns: {sorted(missing)}")

            for _, r in df_ratings.iterrows():
                user_id = int(r.get("userId"))
                movie_id = int(r.get("movieId"))
                rating_value = float(r.get("rating"))

                existing = (
                    session.query(models.Rating)
                    .filter(models.Rating.user_id == user_id, models.Rating.movie_id == movie_id)
                    .first()
                )
                if existing:
                    existing.rating = rating_value
                else:
                    session.add(models.Rating(user_id=user_id, movie_id=movie_id, rating=rating_value))

        session.commit()

        movies_count = session.query(models.Movie).count()
        users_count = session.query(models.User).count()
        ratings_count = session.query(models.Rating).count()
        print(f"Seeded DB: movies={movies_count}, users={users_count}, ratings={ratings_count}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_from_csv()
