from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt
from pydantic import BaseModel

from ..core.database import get_db
from ..core.security import create_token
from ..models.users import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Connexion standard - utilisée par Mobile et Desktop"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="error_auth")

    token = create_token({"sub": str(user.id), "role": user.role, "permissions": user.permissions})
    return {
        "access": token,
        "refresh": token,
        "user": {
            "id": user.id, "full_name": user.full_name, "username": user.username,
            "role": user.role, "permissions": user.permissions,
        }
    }
