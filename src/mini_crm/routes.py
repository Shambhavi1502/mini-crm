
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mini_crm.auth import get_db
from mini_crm.models import User, RefreshToken
from mini_crm.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from mini_crm.security import (
    SECRET_KEY, ALGORITHM, hash_password, verify_password, create_token
)
from mini_crm.auth import get_current_user
from mini_crm.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def issue_tokens(user: User, db: Session):
    access_token, _, _ = create_token(user.id, "access", minutes=15)
    refresh_token, jti, expires = create_token(user.id, "refresh", minutes=60 * 24 * 7)

    db.add(RefreshToken(
        jti=jti,
        user_id=user.id,
        expires_at=expires,
        revoked=False,
    ))
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    user = User(
        username=data.username,
        email=str(data.email),
        hashed_password=hash_password(data.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Registration successful", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(data.email)).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")

    jti = payload.get("jti")
    record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

    if not record or record.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked or unknown")

    record.revoked = True
    db.commit()

    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return issue_tokens(user, db)


@router.post("/logout")
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")

    record = db.query(RefreshToken).filter(
        RefreshToken.jti == payload.get("jti")
    ).first()

    if not record or record.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked or unknown")

    record.revoked = True
    db.commit()
    return {"message": "Logged out successfully"}

@router.get("/auth/me", response_model=UserResponse)
def get_my_profile(current_user=Depends(get_current_user)):
    return current_user
