import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from app.security import (
    get_password_hash, create_access_token,
    decode_access_token, verify_password, get_current_user,
)
from app.store import (
    get_user_by_email, get_user_by_id, create_user, update_user,
    load_users, delete_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    if get_user_by_email(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user_id = str(uuid.uuid4())
    from datetime import datetime
    user = {
        "id": user_id,
        "name": data.name,
        "email": data.email,
        "password_hash": get_password_hash(data.password),
        "role": "user",
        "is_active": "true",
        "created_at": datetime.now().isoformat(),
    }
    create_user(user)
    token = create_access_token({"sub": user["email"], "role": "user", "user_id": user_id})
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user_id, "name": data.name, "email": data.email, "role": "user"},
    }


@router.post("/login")
async def login(data: UserLogin):
    user = get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token({"sub": user["email"], "role": user["role"], "user_id": user["id"]})
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
    }


@router.get("/me")
async def get_me(payload: dict = Depends(get_current_user)):
    user = get_user_by_email(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user["id"], "name": user["name"], "email": user["email"],
        "role": user["role"], "is_active": user.get("is_active") == "true",
        "created_at": user.get("created_at", ""),
    }


@router.put("/me")
async def update_me(data: UserUpdate, payload: dict = Depends(get_current_user)):
    user = get_user_by_email(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updates = {}
    if data.name:
        updates["name"] = data.name
    if data.email:
        updates["email"] = data.email
    if data.password:
        updates["password_hash"] = get_password_hash(data.password)
    update_user(user["id"], updates)
    updated = get_user_by_id(user["id"])
    return {
        "id": updated["id"], "name": updated["name"], "email": updated["email"],
        "role": updated["role"], "is_active": updated.get("is_active") == "true",
        "created_at": updated.get("created_at", ""),
    }
