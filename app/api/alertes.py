from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.alertes import Alerte, AlerteLue

router = APIRouter()


@router.get("")
def get_alertes(page: int = 1, limit: int = 50,
                db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    query = db.query(Alerte).filter(
        (Alerte.destinataire_id.is_(None)) | (Alerte.destinataire_id == current_user.id)
    ).order_by(Alerte.timestamp.desc())
    total = query.count()
    alertes = query.offset((page - 1) * limit).limit(limit).all()

    lues_ids = {r[0] for r in db.query(AlerteLue.alerte_id)
                .filter(AlerteLue.user_id == current_user.id).all()}
    return {
        "total": total, "page": page, "limit": limit,
        "results": [
            {
                "id": a.id, "level": a.niveau, "title": a.type, "type": a.type,
                "message": a.message, "source_module": a.source_module,
                "metadata_json": a.metadata_json,
                "created_at": a.timestamp.isoformat() + "Z",
                "is_read": a.id in lues_ids,
            } for a in alertes
        ],
    }


@router.put("/read-all")
def mark_all_read(db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    visibles = db.query(Alerte.id).filter(
        (Alerte.destinataire_id.is_(None)) | (Alerte.destinataire_id == current_user.id)
    ).all()
    deja_lues = {r[0] for r in db.query(AlerteLue.alerte_id)
                 .filter(AlerteLue.user_id == current_user.id).all()}
    now = datetime.utcnow()
    for (alerte_id,) in visibles:
        if alerte_id not in deja_lues:
            db.add(AlerteLue(alerte_id=alerte_id, user_id=current_user.id, date_lecture=now))
    db.commit()
    return {"status": "ok"}


@router.put("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    a = db.query(Alerte).filter(Alerte.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="error_not_found")
    if a.destinataire_id and a.destinataire_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_alerte_pas_a_vous")
    deja = db.query(AlerteLue).filter(
        AlerteLue.alerte_id == alert_id, AlerteLue.user_id == current_user.id
    ).first()
    if not deja:
        db.add(AlerteLue(alerte_id=alert_id, user_id=current_user.id, date_lecture=datetime.utcnow()))
        db.commit()
    return {"status": "ok"}