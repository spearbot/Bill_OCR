import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app.security import get_current_user
from app.store import get_stats, get_user_by_id, load_users, update_user, delete_user, list_bills_meta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(payload: dict = Depends(get_current_user)):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return payload


@router.get("/stats")
async def stats(payload: dict = Depends(require_admin)):
    return get_stats()


@router.get("/users")
async def list_users(payload: dict = Depends(require_admin)):
    users = load_users()
    return [
        {"id": u.get("id"), "name": u.get("name"), "email": u.get("email"),
         "role": u.get("role"), "is_active": u.get("is_active") == "true",
         "created_at": u.get("created_at", "")}
        for u in users
    ]


@router.put("/users/{user_id}")
async def update_user_admin(user_id: str, data: dict, payload: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_user(user_id, data)
    updated = get_user_by_id(user_id)
    return {"id": updated.get("id"), "name": updated.get("name"), "email": updated.get("email"),
            "role": updated.get("role"), "is_active": updated.get("is_active") == "true"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_admin(user_id: str, payload: dict = Depends(require_admin)):
    if user_id == payload.get("user_id"):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delete_user(user_id)
