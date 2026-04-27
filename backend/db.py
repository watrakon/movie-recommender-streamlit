from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import BASE_DIR


DB_PATH = Path(BASE_DIR) / "data" / "app.db"
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        cols_users = conn.execute(text("PRAGMA table_info(users)"))
        existing_users = {row[1] for row in cols_users}
        if "google_sub" not in existing_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(128)"))
        if "email" not in existing_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))

        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_google_sub ON users (google_sub) WHERE google_sub IS NOT NULL"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email ON users (email) WHERE email IS NOT NULL"))

        cols = conn.execute(text("PRAGMA table_info(movies)"))
        existing = {row[1] for row in cols}
        if "tmdb_id" not in existing:
            conn.execute(text("ALTER TABLE movies ADD COLUMN tmdb_id INTEGER"))
        if "title_th" not in existing:
            conn.execute(text("ALTER TABLE movies ADD COLUMN title_th VARCHAR(255) DEFAULT ''"))
        if "description_th" not in existing:
            conn.execute(text("ALTER TABLE movies ADD COLUMN description_th VARCHAR DEFAULT ''"))

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_movies_tmdb_id ON movies (tmdb_id) WHERE tmdb_id IS NOT NULL"
            )
        )

