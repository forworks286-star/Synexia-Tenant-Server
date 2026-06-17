from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel

from ..core.database import get_db
from ..core.security import create_token
from ..models.users import User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"])

class LoginRequest(BaseModel):
    username: str
    password: str

class PinLoginRequest(BaseModel):
    pin_code: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """دخول عادي - يُستخدم في Mobile و Desktop"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = create_token({"sub": str(user.id), "role": user.role, "permissions": user.permissions})
    return {
        "access": token,
        "user": {
            "id": user.id, "full_name": user.full_name, "username": user.username,
            "role": user.role, "permissions": user.permissions,
        }
    }

@router.post("/login-pin")
def login_pin(req: PinLoginRequest, db: Session = Depends(get_db)):
    """دخول سريع بـ PIN - يُستخدم في الـ Kiosk فقط"""
    users = db.query(User).filter(User.pin_code_hash.isnot(None)).all()
    user = next((u for u in users if pwd_context.verify(req.pin_code, u.pin_code_hash)), None)
    if not user:
        raise HTTPException(status_code=401, detail="Code PIN incorrect")

    token = create_token({"sub": str(user.id), "role": user.role, "permissions": user.permissions})
    return {"access": token, "user": {"id": user.id, "full_name": user.full_name, "role": user.role}}
