from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.database import get_db
from ..core.security import create_access_token, create_refresh_token, decode_token, get_current_user
from ..models.users import User
from ..services.audit_service import enregistrer_audit

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        if user:
            enregistrer_audit(db, user_id=user.id, action="login_failed",
                              table_cible="users", enregistrement_id=user.id)
        raise HTTPException(status_code=401, detail="error_auth")

    user.last_login = datetime.utcnow()
    db.commit()
    enregistrer_audit(db, user_id=user.id, action="login",
                      table_cible="users", enregistrement_id=user.id)

    token_data = {"sub": str(user.id), "role": user.role, "permissions": user.permissions or []}
    return {
        "access": create_access_token(token_data),
        "refresh": create_refresh_token({"sub": str(user.id)}),
        "user": {
            "id": user.id, "full_name": user.full_name,
            "username": user.username, "role": user.role,
            "permissions": user.permissions or [],
        },
    }


@router.post("/refresh")
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="error_token_invalid")
    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="error_user_inactive")
    token_data = {"sub": str(user.id), "role": user.role, "permissions": user.permissions or []}
    return {
        "access": create_access_token(token_data),
        "refresh": create_refresh_token({"sub": str(user.id)}),
    }


@router.post("/logout")
def logout(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    enregistrer_audit(db, user_id=current_user.id, action="logout",
                      table_cible="users", enregistrement_id=current_user.id)
    return {"status": "ok"}


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id, "full_name": current_user.full_name,
        "username": current_user.username, "role": current_user.role,
        "permissions": current_user.permissions or [],
    }
