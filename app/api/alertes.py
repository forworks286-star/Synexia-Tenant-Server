from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from ..core.database import get_db
from ..core.security import get_current_user, verify_device_key
from ..core.ws_manager import ws_manager
from ..models.alertes import Alerte

router = APIRouter()


@router.get("")
def get_alertes(
    page: int = 1, limit: int = 50,
    non_lues: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Alerte).order_by(Alerte.timestamp.desc())
    if non_lues is True:
        query = query.filter(Alerte.lu == False)
    total = query.count()
    alertes = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total, "page": page, "limit": limit,
        "results": [
            {
                "id": a.id, "level": a.niveau, "title": a.type,
                "message": a.message, "source_module": a.source_module,
                "metadata_json": a.metadata_json,
                "created_at": str(a.timestamp), "is_read": a.lu,
            } for a in alertes
        ],
    }


@router.put("/read-all")
def mark_all_read(db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    db.query(Alerte).filter(Alerte.lu == False).update({"lu": True})
    db.commit()
    return {"status": "ok"}


@router.put("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    a = db.query(Alerte).filter(Alerte.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="error_not_found")
    a.lu = True
    db.commit()
    return {"status": "ok"}


class AlerteInternalRequest(BaseModel):
    type: str
    niveau: str = "info"
    message: str
    source_module: str
    metadata_json: dict = {}


@router.post("/internal")
async def create_alerte_internal(
    req: AlerteInternalRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    """Internal endpoint — called by integration services. Protected by X-Device-Key."""
    alerte = Alerte(
        type=req.type, niveau=req.niveau, message=req.message,
        source_module=req.source_module, metadata_json=req.metadata_json,
        timestamp=datetime.utcnow(), lu=False,
    )
    db.add(alerte)
    db.commit()
    await ws_manager.broadcast({
        "id": alerte.id, "type": alerte.type, "niveau": alerte.niveau,
        "message": alerte.message, "source_module": alerte.source_module,
        "timestamp": str(alerte.timestamp),
    })
    return {"status": "ok", "id": alerte.id}
