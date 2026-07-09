from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.database import get_db
from ..core.config import settings
from ..core.security import create_access_token, create_refresh_token, decode_token, get_current_user, generate_jti
from ..models.users import User
from ..models.auth_sessions import RefreshSession
from ..services.audit_service import enregistrer_audit
from sqlalchemy import or_

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

   
    db.query(RefreshSession).filter(
        or_(RefreshSession.expires_at < datetime.utcnow(), RefreshSession.revoked == True)
    ).delete(synchronize_session=False)

    jti = generate_jti()
    session = RefreshSession(
        user_id=user.id, current_jti=jti,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False, created_at=datetime.utcnow(), last_used_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    token_data = {"sub": str(user.id), "role": user.role, "permissions": user.permissions or []}
    return {
        "access": create_access_token(token_data),
        "refresh": create_refresh_token({"sub": str(user.id), "sid": session.id, "jti": jti}),
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

    session = db.query(RefreshSession).filter(RefreshSession.id == payload.get("sid")).first()
    if not session or session.revoked or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="error_token_invalid")

    if session.current_jti != payload.get("jti"):
        # refresh token قديم تم استبداله من قبل — إعادة استعمال = مؤشر سرقة
        session.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="error_session_compromised")

    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="error_user_inactive")

    new_jti = generate_jti()
    session.current_jti = new_jti
    session.expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session.last_used_at = datetime.utcnow()
    db.commit()

    token_data = {"sub": str(user.id), "role": user.role, "permissions": user.permissions or []}
    return {
        "access": create_access_token(token_data),
        "refresh": create_refresh_token({"sub": str(user.id), "sid": session.id, "jti": new_jti}),
    }


@router.post("/logout")
def logout(req: RefreshRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload and payload.get("sid"):
        session = db.query(RefreshSession).filter(RefreshSession.id == payload.get("sid")).first()
        if session:
            session.revoked = True
            db.commit()
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
