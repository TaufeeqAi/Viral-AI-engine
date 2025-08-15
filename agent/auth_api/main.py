import os
from datetime import timedelta
from typing import List
from contextlib import asynccontextmanager
import logging
import uuid
from .auth import email_verification_tokens
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db_core.core import get_db, create_tables
from ..db_core.models.user import User
from .models import UserCreate, UserInDB, Token, RefreshTokenRequest, UserUpdate
from .auth import (
    authenticate_user, create_user, get_user_by_username, get_user_by_email,
    create_access_token, create_refresh_token, verify_token, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES, send_verification_email
)

# --------- Logging Setup ---------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"[DEBUG] JWT_SECRET_KEY:{os.getenv('JWT_SECRET_KEY')}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[APP] Starting up...")
    await create_tables()  # ✅ DB setup
    print("[APP] Startup complete.")
    yield
    print("[APP] Shutting down...")

app = FastAPI(
    title="Cyrene AI Authentication Service",
    description="Advanced authentication service with user management",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, "access")
    if token_data is None:
        raise credentials_exception

    user = await get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = await get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = await create_user(db=db, user=user)

    # Create and store verification token
    token = str(uuid.uuid4())
    email_verification_tokens[token] = new_user.username

    logger.info(f"[VERIFY] Token created for {new_user.username}: {token}")
    # In production, you'd send this via email
    print(f"[VERIFY] Email verification link: http://localhost:8001/verify-email?token={token}")

    return new_user

@app.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    username = email_verification_tokens.pop(token, None)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_username(db, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return {"message": f"Email verified for user {username}"}

@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

  
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": user.username})
    if not user.is_verified:
            return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "is_verified": user.is_verified,
        "email": user.email
    }
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token_data = verify_token(refresh_request.refresh_token, "refresh")
    if token_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await get_user_by_username(db, username=token_data.username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "refresh_token": refresh_request.refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.get("/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.put("/me", response_model=UserInDB)
async def update_user_me(user_update: UserUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    update_data = user_update.dict(exclude_unset=True)

    if "username" in update_data and update_data["username"] != current_user.username:
        existing_user = await get_user_by_username(db, update_data["username"])
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

    if "email" in update_data and update_data["email"] != current_user.email:
        existing_user = await get_user_by_email(db, update_data["email"])
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user

@app.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    return {"message": "Successfully logged out"}

@app.get("/users", response_model=List[UserInDB])
async def list_users(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@app.get("/validate_token")
async def validate_token(current_user: User = Depends(get_current_active_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "message": "Token is valid"
    }


    # POST /resend-verification
@app.post("/resend-verification")
async def resend_verification_email(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.json()
    email = form.get("email")

    user = await get_user_by_email(db, email=email)
    if not user or user.is_verified:
        raise HTTPException(status_code=400, detail="Invalid or already verified")

    await send_verification_email(user.email) 
    return {"message": "Verification email sent"}
