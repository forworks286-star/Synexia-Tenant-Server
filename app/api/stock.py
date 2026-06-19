from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from ..core.database import get_db
from ..models.produits import Produit, Lot
from ..models.mouvements import Mouvement
from ..models.tenant_config import TenantConfig
from ..services.fefo_service import verifier_fefo, FefoViolationError

router = APIRouter()

@router.post("/scan")
def scan_produit(data: dict, db: Session = Depends(get_db)):
    qr_code = data.get("qr_code", "")
    """مسح QR - الخطوة الإلزامية الأولى، لا بحث نصي مسموح"""
    produit = db.query(Produit).filter(Produit.qr_code == qr_code).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    lots = [
        {"id": l.id, "quantite": l.quantite, "date_expiration": l.date_expiration, "emplacement": l.emplacement}
        for l in produit.lots if l.quantite > 0
    ]
    return {
        "id": produit.id, "nom": produit.nom, "qr_code": produit.qr_code,
        "champs_extra": produit.champs_extra, "lots": lots,
    }


class MouvementRequest(BaseModel):
    produit_id: int
    lot_id: int
    type: str  # entree | sortie
    quantite: int
    photo_preuve_url: Optional[str] = None
    user_id: int
    source_device: str  # kiosk | mobile | desktop


@router.post("/mouvements")
def enregistrer_mouvement(req: MouvementRequest, db: Session = Depends(get_db)):
    """
    تسجيل حركة - يطبّق كل القيود: FEFO + الصورة الإلزامية حسب tenant_config
    """
    config = db.query(TenantConfig).first()

    # قيد 1: الصورة الإلزامية
    if config.module_photo_obligatoire and not req.photo_preuve_url:
        raise HTTPException(status_code=400, detail="Photo de preuve obligatoire avant validation")

    # قيد 2: FEFO
    if req.type == "sortie":
        try:
            verifier_fefo(db, req.produit_id, req.lot_id, config)
        except FefoViolationError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"Action refusée. Produits avec date de péremption plus proche doivent sortir en priorité.",
                    "lot_correct_id": e.lot_correct.id,
                    "emplacement": e.lot_correct.emplacement,
                }
            )

    lot = db.query(Lot).filter(Lot.id == req.lot_id).first()
    if not lot or lot.quantite < req.quantite and req.type == "sortie":
        raise HTTPException(status_code=400, detail="Quantité insuffisante dans ce lot")

    if req.type == "entree":
        lot.quantite += req.quantite
    else:
        lot.quantite -= req.quantite

    mouvement = Mouvement(
        produit_id=req.produit_id, lot_id=req.lot_id, type=req.type,
        quantite=req.quantite, photo_preuve_url=req.photo_preuve_url,
        user_id=req.user_id, source_device=req.source_device,
        timestamp=datetime.utcnow(), synced=True,
    )
    db.add(mouvement)
    db.commit()

    return {"status": "ok", "nouvelle_quantite_lot": lot.quantite}
    
@router.get("/mouvements")
def get_mouvements(limit: int = 50, db: Session = Depends(get_db)):
    return {"results": [{"id": m.id, "product_id": m.produit_id, "product_name": "", "type": "entry" if m.type == "entree" else "exit", "quantity": m.quantite, "date": str(m.timestamp), "user_name": ""} for m in db.query(Mouvement).limit(limit).all()]}
    
@router.get("/produits")
def get_produits(db: Session = Depends(get_db)):
    return {"results": [{"id": p.id, "name": p.nom, "qr_reference": p.qr_code, "stock_quantity": sum(l.quantite for l in p.lots), "alert_threshold": p.seuil_critique, "supplier_name": None, "supplier_id": p.fournisseur_id} for p in db.query(Produit).all()]}
