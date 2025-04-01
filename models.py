from pydantic import BaseModel
from typing import Optional


# Модели данных
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    password: str


class TokenVerify(BaseModel):
    username: str
    token: str


class TokenRefresh(BaseModel):
    username: str
    refresh_token: str
