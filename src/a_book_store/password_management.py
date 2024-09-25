from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from fastapi import status, Depends
from fastapi.security import OAuth2PasswordBearer

from a_book_store.config import Config
from a_book_store.models import UserInDB

from pymongo import MongoClient


# Secret key to encode the JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password hash function
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# Password hashing function
def get_password_hash(password):
    return pwd_context.hash(password)


# JWT token creation function
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# JWT token validation function
def verify_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


# Token URL endpoint for OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
DB_NAME = "a_book_store"
USER_COLLECTION = "user"


def get_user_fromdb(username: str):
    try:
        config = Config()
        mongo_client = MongoClient(config.database_uri)
        result = mongo_client[DB_NAME][USER_COLLECTION].find_one({"username": username})
        return UserInDB(**result)
    except Exception as exc:
        f"Error while fetching user with error {exc}"


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_fromdb(username)
    if user is None:
        raise credentials_exception
    return user


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(username: str, password: str):
    user = get_user_fromdb(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
