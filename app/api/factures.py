from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..models.factures import Facture
from ..services.audit_service import enregistrer_audit

router = APIRouter()


@router.get("")
def get_factures(page: int = 1, limit: int = 50,
                 db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    total = db.query(Facture).count()
    factures = db.query(Facture).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total, "page": page, "limit": limit,
        "results": [
            {
                "id": f.id, "supplier_name": f.fournisseur_nom,
                "date": str(f.date),
                "amount_ht": f.montant_ht, "amount_tva": f.montant_tva,
                "amount_ttc": f.montant_ttc, "ppa": f.ppa,
                "status": f.statut, "photo_url": f.image_url,
                "incoherence_detectee": f.incoherence_detectee,
                "stamp_detected": True, "signature_detected": True,
            } for f in factures
        ],
    }


@router.put("/{facture_id}/valider")
def valider(facture_id: int, db: Session = Depends(get_db),
            current_user=Depends(require_role("admin", "manager"))):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="error_not_found")
    f.statut = "validated"
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_validee",
                      table_cible="factures", enregistrement_id=f.id)
    return {"status": "ok"}


@router.put("/{facture_id}/rejeter")
def rejeter(facture_id: int, db: Session = Depends(get_db),
            current_user=Depends(require_role("admin", "manager"))):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="error_not_found")
    f.statut = "rejected"
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_rejetee",
                      table_cible="factures", enregistrement_id=f.id)
    return {"status": "ok"}
