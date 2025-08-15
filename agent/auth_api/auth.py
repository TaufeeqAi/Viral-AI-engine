import os
from datetime import datetime, timedelta
from typing import Optional, Union
import base64
import logging
import uuid
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from ..db_core.models.user import User
from .models import UserCreate, TokenData

# --------- Logging Setup ---------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = base64.b64decode(os.getenv("JWT_SECRET_KEY"))
REFRESH_SECRET_KEY = base64.b64decode(os.getenv("JWT_REFRESH_SECRET_KEY"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

email_verification_tokens = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    is_valid = pwd_context.verify(plain_password, hashed_password)
    logger.debug("verify_password: %s -> %s", plain_password, is_valid)
    return is_valid


def get_password_hash(password: str) -> str:
    """Hash a password."""
    hashed = pwd_context.hash(password)
    logger.debug("get_password_hash: generated hash for password")
    return hashed


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("create_access_token: token created for %s", data.get("sub"))
    return token


def create_refresh_token(data: dict) -> str:
    """Create refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    logger.info("create_refresh_token: refresh token created for %s", data.get("sub"))
    return token


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify and decode token."""
    try:
        secret_key = SECRET_KEY if token_type == "access" else REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            logger.warning("verify_token: token type mismatch. expected %s, got %s", token_type, payload.get("type"))
            return None
        username: str = payload.get("sub")
        if username is None:
            logger.warning("verify_token: missing subject in token")
            return None
        logger.debug("verify_token: token verified for %s", username)
        return TokenData(username=username)
    except JWTError as e:
        logger.error("verify_token: JWTError %s", e)
        return None


# User CRUD operations
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    logger.debug("get_user_by_username: querying for username %s", username)
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user:
        logger.info("get_user_by_username: found user %s", username)
    else:
        logger.warning("get_user_by_username: user not found %s", username)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    logger.debug("get_user_by_email: querying for email %s", email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        logger.info("get_user_by_email: found email %s", email)
    else:
        logger.warning("get_user_by_email: email not found %s", email)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    logger.debug("get_user_by_id: querying for user_id %s", user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user:
        logger.info("get_user_by_id: found user id %s", user_id)
    else:
        logger.warning("get_user_by_id: user_id not found %s", user_id)
    return user


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    logger.info("create_user: creating user %s", user.username)
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info("create_user: user created %s", user.username)
    return db_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Union[User, bool]:
    logger.debug("authenticate_user: authenticating %s", username)
    user = await get_user_by_username(db, username)
    if not user:
        logger.warning("authenticate_user: user not found %s", username)
        return False
    if not verify_password(password, user.hashed_password):
        logger.warning("authenticate_user: invalid password for %s", username)
        return False
    logger.info("authenticate_user: authentication successful for %s", username)
    return user


async def send_verification_email(db: AsyncSession, user: User):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = str(uuid.uuid4())
    username = user.username
    email_verification_tokens[token] = username
    print(f"[VERIFY] Email verification link: http://localhost:8001/verify-email?token={token}")