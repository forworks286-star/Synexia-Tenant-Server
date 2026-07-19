from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.factures import Facture
from ..models.lignes_facture import LigneFacture
from ..services.audit_service import enregistrer_audit
from ..services.stock_service import appliquer_lignes_facture

router = APIRouter()


def _facture_to_dict(f: Facture) -> dict:
    return {
        "id": f.id, "supplier_name": f.fournisseur_nom,
        "date": str(f.date), "type_facture": f.type_facture,
        "amount_ht": f.montant_ht, "amount_tva": f.montant_tva,
        "amount_ttc": f.montant_ttc, "taux_tva": f.taux_tva, "ppa": f.ppa,
        "numero_facture": f.numero_facture,
        "fournisseur_nif": f.fournisseur_nif, "fournisseur_nis": f.fournisseur_nis,
        "fournisseur_rc": f.fournisseur_rc,
        "status": f.statut, "photo_url": f.image_url,
        "incoherence_detectee": f.incoherence_detectee,
        "cree_manuellement": f.cree_manuellement, "motif_rejet": f.motif_rejet,
        "motif_creation_manuelle": f.motif_creation_manuelle,
        "cree_par_id": f.cree_par_id,
        "stamp_detected": True, "signature_detected": True,
    }


@router.get("")
def get_factures(page: int = 1, limit: int = 50, type_facture: Optional[str] = None,
                 db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Facture)
    if type_facture:
        query = query.filter(Facture.type_facture == type_facture)
    # Session privee : un stockiste/agent ne voit que ses propres factures.
    # admin et manager voient tout (supervision).
    if current_user.role not in ("admin", "manager"):
        query = query.filter(Facture.cree_par_id == current_user.id)
    total = query.count()
    factures = query.order_by(Facture.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit,
            "results": [_facture_to_dict(f) for f in factures]}


class FactureManuelleRequest(BaseModel):
    fournisseur_nom: str
    date: str
    type_facture: str = "achat"  # achat | vente
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    taux_tva: float = 19.0
    motif_creation_manuelle: str


@router.post("/manuelle")
async def creer_facture_manuelle(req: FactureManuelleRequest, db: Session = Depends(get_db),
                                  current_user=Depends(get_current_user)):
    if not req.motif_creation_manuelle or not req.motif_creation_manuelle.strip():
        raise HTTPException(status_code=400, detail="error_motif_requis")
    from ..api.integrations import _generate_numero_facture
    try:
        date_facture = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="error_date_invalide")
    facture = Facture(
        fournisseur_nom=req.fournisseur_nom, date=date_facture,
        montant_ht=req.montant_ht, montant_tva=req.montant_tva, montant_ttc=req.montant_ttc,
        taux_tva=req.taux_tva, numero_facture=_generate_numero_facture(db),
        type_facture=req.type_facture, statut="pending",
        cree_manuellement=True, motif_creation_manuelle=req.motif_creation_manuelle.strip(),
        cree_par_id=current_user.id,
    )
    db.add(facture)
    db.commit()
    db.refresh(facture)
    enregistrer_audit(db, user_id=current_user.id, action="facture_creee_manuellement",
                      table_cible="factures", enregistrement_id=facture.id,
                      apres={"motif": req.motif_creation_manuelle})
    from ..services.alertes_service import creer_alerte
    await creer_alerte(
        db, type="facture", niveau="warning",
        message=f"Facture creee manuellement par {current_user.full_name} — verification requise",
        source="facture_manuelle",
        meta={"facture_id": facture.id, "user_id": current_user.id},
    )
    await ws_manager.broadcast({
        "type": "new_facture", "id": facture.id,
        "fournisseur_nom": req.fournisseur_nom, "montant_ttc": req.montant_ttc,
        "cree_manuellement": True,
    })
    return _facture_to_dict(facture)


@router.get("/{facture_id}")
def get_facture(facture_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="error_not_found")
    return _facture_to_dict(f)


@router.put("/{facture_id}/valider")
async def valider(facture_id: int, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin", "manager"))):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="error_not_found")
    if f.statut != "pending":
        raise HTTPException(status_code=400, detail="error_facture_deja_traitee")

    lignes = db.query(LigneFacture).filter(LigneFacture.facture_id == facture_id).all()
    if lignes:
        total_lignes = round(sum(l.montant_ligne for l in lignes), 2)
        if abs(total_lignes - f.montant_ht) > 0.5:
            f.incoherence_detectee = True
        appliquer_lignes_facture(db, f, lignes, current_user)

    f.statut = "validated"
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_validee",
                      table_cible="factures", enregistrement_id=f.id)

    for l in lignes:
        await ws_manager.broadcast({
            "type": "stock_update", "produit_id": l.produit_id, "nouvelle_quantite": None,
        })
    await ws_manager.broadcast({"type": "facture_update", "id": f.id, "status": "validated"})
    return {"status": "ok"}


class RejeterRequest(BaseModel):
    motif: str


@router.put("/{facture_id}/rejeter")
async def rejeter(facture_id: int, req: RejeterRequest, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin", "manager"))):
    f = db.query(Facture).filter(Facture.id == facture_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="error_not_found")
    if f.statut != "pending":
        raise HTTPException(status_code=400, detail="error_facture_deja_traitee")
    if not req.motif or not req.motif.strip():
        raise HTTPException(status_code=400, detail="error_motif_requis")
    f.statut = "rejected"
    f.motif_rejet = req.motif.strip()
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_rejetee",
                      table_cible="factures", enregistrement_id=f.id, apres={"motif": req.motif})
    await ws_manager.broadcast({"type": "facture_update", "id": f.id, "status": "rejected"})
    return {"status": "ok"}