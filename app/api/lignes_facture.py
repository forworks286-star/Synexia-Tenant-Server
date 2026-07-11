from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..models.factures import Facture
from ..models.produits import Produit
from ..models.lignes_facture import LigneFacture
from ..services.stock_service import trouver_produit_correspondant

router = APIRouter()


class LigneCreateRequest(BaseModel):
    produit_id: Optional[int] = None
    designation: Optional[str] = None
    type_stock: Optional[str] = None
    quantite: float
    prix_unitaire: float


def _ligne_to_dict(l: LigneFacture) -> dict:
    return {
        "id": l.id, "facture_id": l.facture_id, "produit_id": l.produit_id,
        "produit_nom": l.produit.nom if l.produit else l.designation_brute,
        "designation_brute": l.designation_brute,
        "type_stock": l.type_stock or (l.produit.type_stock if l.produit else None),
        "matched": l.produit_id is not None,
        "quantite": l.quantite, "prix_unitaire": l.prix_unitaire,
        "montant_ligne": l.montant_ligne, "source": l.source,
        "facture_date": str(l.facture.date), "fournisseur_nom": l.facture.fournisseur_nom,
        "type_facture": l.facture.type_facture, "numero_facture": l.facture.numero_facture,
    }


@router.post("/factures/{facture_id}/lignes")
def ajouter_ligne(facture_id: int, req: LigneCreateRequest, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin", "manager"))):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_facture_not_found")
    if facture.statut != "pending":
        raise HTTPException(status_code=400, detail="error_facture_deja_traitee")

    produit_id = req.produit_id
    if not produit_id and req.designation:
        trouve = trouver_produit_correspondant(db, req.designation)
        if trouve:
            produit_id = trouve.id
    if not produit_id and not req.designation:
        raise HTTPException(status_code=400, detail="error_produit_ou_designation_requis")
    if not produit_id and not req.type_stock:
        raise HTTPException(status_code=400, detail="error_type_stock_requis")

    produit = db.query(Produit).filter(Produit.id == produit_id).first() if produit_id else None
    ligne = LigneFacture(
        facture_id=facture_id, produit_id=produit_id,
        designation_brute=produit.nom if produit else req.designation,
        type_stock=req.type_stock,
        quantite=req.quantite, prix_unitaire=req.prix_unitaire,
        montant_ligne=round(req.quantite * req.prix_unitaire, 2), source="manuel",
    )
    db.add(ligne)
    db.commit()
    db.refresh(ligne)
    return _ligne_to_dict(ligne)


@router.get("/factures/{facture_id}/lignes")
def lister_lignes(facture_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_facture_not_found")
    lignes = db.query(LigneFacture).filter(LigneFacture.facture_id == facture_id).all()
    return {"results": [_ligne_to_dict(l) for l in lignes]}


@router.delete("/lignes/{ligne_id}")
def supprimer_ligne(ligne_id: int, db: Session = Depends(get_db),
                     current_user=Depends(require_role("admin", "manager"))):
    ligne = db.query(LigneFacture).filter(LigneFacture.id == ligne_id).first()
    if not ligne:
        raise HTTPException(status_code=404, detail="error_ligne_not_found")
    if ligne.facture.statut != "pending":
        raise HTTPException(status_code=400, detail="error_facture_deja_traitee")
    db.delete(ligne)
    db.commit()
    return {"status": "ok"}


@router.get("/produits/{produit_id}/historique-prix")
def historique_prix_produit(produit_id: int, db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="error_produit_not_found")
    lignes = (db.query(LigneFacture).join(Facture, LigneFacture.facture_id == Facture.id)
              .filter(LigneFacture.produit_id == produit_id)
              .order_by(Facture.date.desc()).all())
    historique = [_ligne_to_dict(l) for l in lignes]
    achats = [l["prix_unitaire"] for l in historique if l["type_facture"] in ("achat", "ajustement_manuel")]
    ventes = [l["prix_unitaire"] for l in historique if l["type_facture"] == "vente"]
    prix_achat_moyen = round(sum(achats) / len(achats), 2) if achats else None
    prix_vente_moyen = round(sum(ventes) / len(ventes), 2) if ventes else None
    marge_percent = None
    if prix_achat_moyen and prix_vente_moyen and prix_achat_moyen > 0:
        marge_percent = round((prix_vente_moyen - prix_achat_moyen) / prix_achat_moyen * 100, 2)
    return {
        "produit_id": produit_id, "produit_nom": produit.nom, "historique": historique,
        "prix_achat_moyen": prix_achat_moyen, "prix_vente_moyen": prix_vente_moyen,
        "marge_percent": marge_percent,
    }