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


@router.get("/produits")
def get_produits(db: Session = Depends(get_db)):
    return {"results": [
        {
    "id": p.id, "sku": p.sku, "name": p.nom, "categorie": p.categorie,
    "qr_reference": p.qr_code, "code_barre": p.code_barre,
    "unite_mesure": p.unite_mesure,
    "pays_origine": p.pays_origine,
    "statut_produit": p.statut_produit,
    "stock_quantity": sum(l.quantite for l in p.lots),
    "alert_threshold": p.seuil_critique,
    "prix_achat": p.prix_achat, "prix_vente": p.prix_vente,
    "supplier_name": p.fournisseur.nom if p.fournisseur else None,
    "supplier_id": p.fournisseur_id,
} for p in db.query(Produit).all()
    ]}


@router.post("/scan")
def scan_produit(data: dict, db: Session = Depends(get_db)):
    qr_code = data.get("qr_code", "")
    produit = db.query(Produit).filter(Produit.qr_code == qr_code).first()
    if not produit:
        raise HTTPException(status_code=404, detail="error_not_found")

    lots = [
        {"id": l.id, "quantite": l.quantite, "date_expiration": l.date_expiration, "emplacement": l.emplacement}
        for l in produit.lots if l.quantite > 0
    ]
    return {
        "id": produit.id, "sku": produit.sku, "nom": produit.nom, "qr_code": produit.qr_code,
        "champs_extra": produit.champs_extra, "lots": lots,
    }


class MouvementRequest(BaseModel):
    produit_id: int
    lot_id: int
    type: str
    quantite: int
    photo_preuve_url: Optional[str] = None
    user_id: int
    source_device: str


@router.post("/mouvements")
def enregistrer_mouvement(req: MouvementRequest, db: Session = Depends(get_db)):
    config = db.query(TenantConfig).first()

    if config and config.module_photo_obligatoire and not req.photo_preuve_url:
        raise HTTPException(status_code=400, detail="error_photo_required")

    if req.type == "sortie":
        try:
            verifier_fefo(db, req.produit_id, req.lot_id, config)
        except FefoViolationError as e:
            raise HTTPException(
                status_code=409,
                detail={"message": "error_fefo_violation", "lot_correct_id": e.lot_correct.id, "emplacement": e.lot_correct.emplacement}
            )

    lot = db.query(Lot).filter(Lot.id == req.lot_id).first()
    if not lot or (lot.quantite < req.quantite and req.type == "sortie"):
        raise HTTPException(status_code=400, detail="error_insufficient_stock")

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
    return {"results": [
        {"id": m.id, "product_id": m.produit_id, "product_name": "",
         "type": "entry" if m.type == "entree" else "exit",
         "quantity": m.quantite, "date": str(m.timestamp), "user_name": ""}
        for m in db.query(Mouvement).order_by(Mouvement.timestamp.desc()).limit(limit).all()
    ]}
