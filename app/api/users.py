from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext

from ..core.database import get_db
from ..core.security import require_role, get_current_user
from ..core.config import settings
from ..models.users import User
from ..services.audit_service import enregistrer_audit

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _user_dict(u: User) -> dict:
    return {
        "id": u.id, "full_name": u.full_name, "username": u.username,
        "role": u.role, "permissions": u.permissions or [],
        "is_active": u.is_active,
        "last_login": str(u.last_login) if u.last_login else None,
    }


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    return {"setup_done": db.query(User).count() > 0}


class SetupRequest(BaseModel):
    full_name: str
    username: str
    password: str


@router.post("/setup")
def first_setup(req: SetupRequest, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="setup_already_done")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="error_password_too_short")
    admin = User(
        full_name=req.full_name, username=req.username,
        password_hash=pwd_context.hash(req.password),
        role="admin",
        permissions=["valider_facture", "modifier_stock", "voir_camera", "gerer_utilisateurs"],
        is_active=True, created_at=datetime.utcnow(),
    )
    db.add(admin)
    db.commit()
    return {"status": "ok"}


class SuperAdminVerifyRequest(BaseModel):
    username: str
    password: str


@router.post("/super-admin/verify")
def verify_super_admin(req: SuperAdminVerifyRequest):
    if req.username != settings.SUPER_ADMIN_USERNAME or req.password != settings.SUPER_ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="error_super_admin_invalid")
    return {"status": "ok"}


@router.get("")
def get_users(db: Session = Depends(get_db),
              current_user=Depends(require_role("admin"))):
    return {"results": [_user_dict(u) for u in db.query(User).all()]}


class UserCreateRequest(BaseModel):
    full_name: str
    username: str
    password: str
    role: str = "stockiste"
    permissions: list = []


@router.post("")
def create_user(req: UserCreateRequest, db: Session = Depends(get_db),
                current_user=Depends(require_role("admin"))):
    if req.role == "admin":
        raise HTTPException(status_code=403, detail="error_cannot_create_admin")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail="error_username_exists")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="error_password_too_short")
    user = User(
        full_name=req.full_name, username=req.username,
        password_hash=pwd_context.hash(req.password),
        role=req.role, permissions=req.permissions,
        is_active=True, created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    enregistrer_audit(db, user_id=current_user.id, action="user_created",
                      table_cible="users", enregistrement_id=user.id,
                      apres={"username": user.username, "role": user.role})
    return {"status": "ok", "id": user.id}


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[list] = None
    is_active: Optional[bool] = None


@router.put("/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest,
                db: Session = Depends(get_db),
                current_user=Depends(require_role("admin"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="error_not_found")
    if user_id == current_user.id and req.role and req.role != "admin":
        raise HTTPException(status_code=400, detail="error_cannot_downgrade_self")
    avant = {"role": user.role, "is_active": user.is_active}
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="user_updated",
                      table_cible="users", enregistrement_id=user.id,
                      avant=avant, apres=req.model_dump(exclude_none=True))
    return {"status": "ok"}


@router.put("/{user_id}/reset-password")
def reset_password(user_id: int, data: dict, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="error_not_found")
    new_pw = data.get("new_password", "")
    if len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="error_password_too_short")
    user.password_hash = pwd_context.hash(new_pw)
    db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db),
                    current_user=Depends(require_role("admin"))):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="error_cannot_delete_self")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="error_not_found")
    user.is_active = False
    db.commit()
    return {"status": "ok"}