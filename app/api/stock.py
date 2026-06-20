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
from ..services.audit_service import enregistrer_audit

router = APIRouter()


@router.get("/produits")
def get_produits(db: Session = Depends(get_db)):
    return {"results": [
        {
            "id": p.id, "sku": p.sku, "name": p.nom, "categorie": p.categorie,
            "qr_reference": p.qr_code, "code_barre": p.code_barre,
            "unite_mesure": p.unite_mesure, "numero_serie": p.numero_serie,
            "photo_url": p.photo_url,
            "pays_origine": p.pays_origine, "statut_produit": p.statut_produit,
            "stock_physique": sum(l.quantite_physique for l in p.lots),
            "stock_disponible": sum(l.quantite_disponible for l in p.lots),
            "stock_reserve": sum(l.quantite_reservee for l in p.lots),
            "alert_threshold": p.seuil_critique,
            "stock_securite": p.stock_securite,
            "quantite_min_commande": p.quantite_min_commande,
            "quantite_max_stock": p.quantite_max_stock,
            "prix_achat": p.prix_achat, "prix_moyen_pondere": p.prix_moyen_pondere,
            "prix_vente": p.prix_vente, "taux_tva": p.taux_tva, "devise": p.devise,
            "valeur_stock": round(sum(l.quantite_physique for l in p.lots) * p.prix_moyen_pondere, 2),
            "supplier_name": p.fournisseur.nom if p.fournisseur else None,
            "supplier_id": p.fournisseur_id,
            "supplier_secondaire_name": p.fournisseur_secondaire.nom if p.fournisseur_secondaire else None,
            "delai_livraison_jours": p.fournisseur.delai_livraison_jours if p.fournisseur else None,
        } for p in db.query(Produit).all()
    ]}


@router.post("/scan")
def scan_produit(data: dict, db: Session = Depends(get_db)):
    qr_code = data.get("qr_code", "")
    produit = db.query(Produit).filter(Produit.qr_code == qr_code).first()
    if not produit:
        raise HTTPException(status_code=404, detail="error_not_found")

    lots = [
        {
            "id": l.id, "numero_lot": l.numero_lot,
            "quantite_physique": l.quantite_physique, "quantite_disponible": l.quantite_disponible,
            "statut": l.statut,
            "date_fabrication": l.date_fabrication, "date_expiration": l.date_expiration,
            "emplacement": l.emplacement,
        }
        for l in produit.lots if l.quantite_physique > 0
    ]
    return {
        "id": produit.id, "sku": produit.sku, "nom": produit.nom, "qr_code": produit.qr_code,
        "champs_extra": produit.champs_extra, "lots": lots,
    }


class MouvementRequest(BaseModel):
    produit_id: int
    lot_id: int
    type: str  # entree | sortie | retour
    quantite: int
    photo_preuve_url: Optional[str] = None
    numero_commande_achat: Optional[str] = None
    numero_bl: Optional[str] = None
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
    if not lot or (lot.quantite_disponible < req.quantite and req.type == "sortie"):
        raise HTTPException(status_code=400, detail="error_insufficient_stock")

    quantite_avant = lot.quantite_physique

    if req.type == "entree":
        lot.quantite_physique += req.quantite
    elif req.type == "retour":
        lot.quantite_physique += req.quantite
    else:
        lot.quantite_physique -= req.quantite

    lot.date_dernier_mouvement = datetime.utcnow()
    if req.type == "entree" and not lot.date_entree_stock:
        lot.date_entree_stock = datetime.utcnow()

    mouvement = Mouvement(
        produit_id=req.produit_id, lot_id=req.lot_id, type=req.type,
        quantite=req.quantite, photo_preuve_url=req.photo_preuve_url,
        numero_commande_achat=req.numero_commande_achat, numero_bl=req.numero_bl,
        user_id=req.user_id, source_device=req.source_device,
        timestamp=datetime.utcnow(), synced=True,
    )
    db.add(mouvement)
    db.commit()

    enregistrer_audit(
        db, user_id=req.user_id, action="mouvement_stock", table_cible="lots",
        enregistrement_id=lot.id,
        avant={"quantite_physique": quantite_avant},
        apres={"quantite_physique": lot.quantite_physique},
        source_device=req.source_device,
    )

    return {"status": "ok", "nouvelle_quantite_lot": lot.quantite_physique}


@router.get("/mouvements")
def get_mouvements(limit: int = 50, db: Session = Depends(get_db)):
    return {"results": [
        {
            "id": m.id, "product_id": m.produit_id, "product_name": "",
            "type": "entry" if m.type == "entree" else ("return" if m.type == "retour" else "exit"),
            "quantity": m.quantite,
            "numero_commande_achat": m.numero_commande_achat, "numero_bl": m.numero_bl,
            "date": str(m.timestamp), "user_name": "",
        }
        for m in db.query(Mouvement).order_by(Mouvement.timestamp.desc()).limit(limit).all()
    ]}
