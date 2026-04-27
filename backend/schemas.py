from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=100)


class User(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        orm_mode = True


class RatingWithMovie(BaseModel):
    user_id: int
    username: str
    movie_id: int
    title: str
    rating: float
    created_at: datetime


class RatingWithUser(BaseModel):
    user_id: int
    username: str
    movie_id: int
    rating: float
    created_at: datetime


class MovieRatingSummary(BaseModel):
    movie_id: int
    count: int
    average: float


class MovieBase(BaseModel):
    tmdb_id: Optional[int] = None
    title: str
    title_th: Optional[str] = ""
    genres: Optional[str] = ""
    description: Optional[str] = ""
    description_th: Optional[str] = ""
    poster_url: Optional[str] = ""


class MovieCreate(MovieBase):
    pass


class Movie(MovieBase):
    id: int

    class Config:
        orm_mode = True


class RatingCreate(BaseModel):
    movie_id: int
    rating: float = Field(ge=0, le=5)


class Rating(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: float
    created_at: datetime

    class Config:
        orm_mode = True


class Recommendation(BaseModel):
    title: str
    genres: str
    score: float


class UserActivityBase(BaseModel):
    activity_type: str
    movie_id: Optional[int] = None
    query: Optional[str] = None
    details: Optional[str] = None


class UserActivityCreate(UserActivityBase):
    pass


class UserActivity(UserActivityBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

