from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.factures import Facture

router = APIRouter()

@router.get("")
def get_factures(db: Session = Depends(get_db)):
    return {"results": [{"id": f.id, "supplier_name": f.fournisseur_nom, "date": str(f.date), "amount_ht": f.montant_ht, "amount_ttc": f.montant_ttc, "stamp_detected": True, "signature_detected": True, "status": f.statut, "photo_url": f.image_url} for f in db.query(Facture).all()]}

@router.put("/{facture_id}/valider")
def valider(facture_id: int, db: Session = Depends(get_db)):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f: raise HTTPException(status_code=404)
    f.statut = "validated"
    db.commit()
    return {"status": "ok"}

@router.put("/{facture_id}/rejeter")
def rejeter(facture_id: int, db: Session = Depends(get_db)):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f: raise HTTPException(status_code=404)
    f.statut = "rejected"
    db.commit()
    return {"status": "ok"}
