from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Book(BaseModel):
    title: str
    description: Optional[str]
    genre: str
    author: str
    published_year: str
    price: float
    created_at: datetime = datetime.now()
    last_modified_at: datetime
    last_modified_by: str


class ColorEnum(str, Enum):
    admin = "admin"
    user = "user"


class User(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserInDB(User):
    hashed_password: str
