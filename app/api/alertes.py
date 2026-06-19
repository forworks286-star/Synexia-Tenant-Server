from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.alertes import Alerte

router = APIRouter()

@router.get("")
def get_alertes(db: Session = Depends(get_db)):
    return {"results": [{"id": a.id, "level": a.niveau, "title": a.type, "message": a.message, "created_at": str(a.timestamp), "is_read": a.lu} for a in db.query(Alerte).all()]}

@router.put("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(Alerte).filter(Alerte.id == alert_id).first()
    if a:
        a.lu = True
        db.commit()
    return {"status": "ok"}