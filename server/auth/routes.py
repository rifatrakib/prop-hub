from typing import Union
from jose import JWTError, jwt
from pydantic import ValidationError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from ..database import read_config

from .crud import create_user, read_user, is_exist_user, read_user_with_id
from .schemas import Token, TokenData, User, UserCreate, UserWithID, UserInDB, Encoder

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    user_data = read_user(username)
    if user_data:
        return UserInDB(**user_data)


def read_secrets():
    secret_key = read_config("secret_key")
    algorithm = read_config("algorithm")
    return Encoder(secret_key=secret_key, algorithm=algorithm)


def authenticate_user(username: str, password: str):
    user = get_user(username)
    
    if not user:
        return False
    
    if not verify_password(password, user.hashed_password):
        return False
    
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    encoder_kw: Encoder = read_secrets()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, encoder_kw.secret_key, algorithm=encoder_kw.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    encoder_kw: Encoder = read_secrets()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, encoder_kw.secret_key, algorithms=[encoder_kw.algorithm])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if not user:
        raise credentials_exception
    
    return user


async def get_access_token(user: User):
    access_token_expires = timedelta(minutes=read_config("access_token_expire_minutes"))
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/token/", response_model=Token, tags=["user"])
async def read_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = await get_access_token(user)
    return token


@router.get("/users/me/", response_model=UserWithID, tags=["user"])
def read_users_me(current_user: User = Depends(get_current_user)):
    user_data = read_user_with_id(current_user.username)
    user_data["id"] = str(user_data["_id"])
    return user_data


@router.post("/users/", response_model=Token, tags=["user"])
async def create_new_user(raw_user: UserCreate = Body()):
    is_exist = is_exist_user(raw_user.username)
    if is_exist:
        raise HTTPException(status_code=400, detail="username already exists")
    
    hashed_password = get_password_hash(raw_user.password)
    user_data = UserInDB(
        username=raw_user.username,
        fullname=raw_user.fullname,
        hashed_password=hashed_password,
    )
    
    user_data = create_user(user_data)
    token = await get_access_token(user_data)
    return token
