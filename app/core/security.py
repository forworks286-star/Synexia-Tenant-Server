from datetime import datetime, timedelta
from jose import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["type"] = "access"
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload["type"] = "refresh"
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from ..models.users import User
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="error_token_invalid")
    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="error_user_inactive")
    return user


def require_role(*roles: str):
    """Check user role — usage: Depends(require_role('admin', 'manager'))"""
    def dependency(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="error_forbidden")
        return current_user
    return dependency


def require_permission(permission: str):
    """Check fine-grained permission — usage: Depends(require_permission('valider_facture'))"""
    def dependency(current_user=Depends(get_current_user)):
        if current_user.role == "admin":
            return current_user
        if permission not in (current_user.permissions or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="error_forbidden")
        return current_user
    return dependency


def verify_device_key(x_device_key: str = Header(...)):
    """Device key protection for IA/IoT endpoints — add as Depends"""
    if x_device_key != settings.DEVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="error_invalid_device_key")
