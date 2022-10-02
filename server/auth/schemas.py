from typing import Union

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class User(BaseModel):
    username: str
    fullname: Union[str, None] = None


class UserCreate(User):
    password: str


class UserWithID(User):
    id: str


class UserInDB(User):
    hashed_password: str


class Encoder(BaseModel):
    secret_key: str
    algorithm: str
