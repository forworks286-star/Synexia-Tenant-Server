import secrets
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..core.ws_manager import ws_manager
from ..models.appairage import SessionAppairage

router = APIRouter()

DUREE_VALIDITE_MINUTES = 3


class GenererCodeRequest(BaseModel):
    type_stock: str
    type_facture: str = "achat"


@router.post("/generer")
def generer_code(req: GenererCodeRequest, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    db.query(SessionAppairage).filter(
        SessionAppairage.cree_par_id == current_user.id,
        SessionAppairage.statut == "attente",
    ).update({"statut": "expire"})

    code = f"{secrets.randbelow(1000000):06d}"
    session = SessionAppairage(
        code=code, cree_par_id=current_user.id,
        type_stock=req.type_stock, type_facture=req.type_facture,
        statut="attente", date_creation=datetime.utcnow(),
        date_expiration=datetime.utcnow() + timedelta(minutes=DUREE_VALIDITE_MINUTES),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "code": code, "expire_dans_secondes": DUREE_VALIDITE_MINUTES * 60,
        "type_stock": req.type_stock, "type_facture": req.type_facture,
    }


@router.post("/{code}/scanner")
async def scanner_code(code: str, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    session = db.query(SessionAppairage).filter(SessionAppairage.code == code).first()
    if not session:
        raise HTTPException(status_code=404, detail="error_code_invalide")
    if session.statut != "attente":
        raise HTTPException(status_code=400, detail="error_code_deja_utilise")
    if session.date_expiration < datetime.utcnow():
        session.statut = "expire"
        db.commit()
        raise HTTPException(status_code=400, detail="error_code_expire")

    session.statut = "scanne"
    db.commit()
    await ws_manager.send_to_user(session.cree_par_id, {
        "type": "appairage_update", "code": code, "statut": "scanne",
    })
    return {"status": "ok", "type_stock": session.type_stock, "type_facture": session.type_facture}


@router.get("/{code}/statut")
def statut_code(code: str, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    session = db.query(SessionAppairage).filter(SessionAppairage.code == code).first()
    if not session:
        raise HTTPException(status_code=404, detail="error_code_invalide")
    return {"statut": session.statut, "facture_id": session.facture_id}