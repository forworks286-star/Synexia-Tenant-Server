from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..models.factures import Facture
from ..services.audit_service import enregistrer_audit

router = APIRouter()


@router.get("")
def get_factures(page: int = 1, limit: int = 50,
                 type_facture: Optional[str] = None,
                 db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    query = db.query(Facture)
    if type_facture:
        query = query.filter(Facture.type_facture == type_facture)
    total = query.count()
    factures = query.order_by(Facture.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total, "page": page, "limit": limit,
        "results": [
            {
                "id": f.id, "supplier_name": f.fournisseur_nom,
                "date": str(f.date), "type_facture": f.type_facture,
                "amount_ht": f.montant_ht, "amount_tva": f.montant_tva,
                "amount_ttc": f.montant_ttc, "taux_tva": f.taux_tva, "ppa": f.ppa,
                "numero_facture": f.numero_facture,
                "fournisseur_nif": f.fournisseur_nif, "fournisseur_nis": f.fournisseur_nis,
                "fournisseur_rc": f.fournisseur_rc,
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
