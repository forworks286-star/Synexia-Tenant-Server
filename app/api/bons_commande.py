from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.bon_commande import BonCommande, LigneBonCommande

router = APIRouter()


def _bc_to_dict(bc: BonCommande) -> dict:
    return {
        "id": bc.id, "numero_bc": bc.numero_bc, "type_stock": bc.type_stock,
        "fournisseur_nom": bc.fournisseur_nom, "statut": bc.statut,
        "date_creation": bc.date_creation.isoformat() + "Z",
        "lignes": [
            {"id": l.id, "produit_id": l.produit_id, "designation": l.designation,
             "quantite": l.quantite, "prix_unitaire_estime": l.prix_unitaire_estime}
            for l in bc.lignes
        ],
    }


class LigneBCRequest(BaseModel):
    produit_id: Optional[int] = None
    designation: str
    quantite: float
    prix_unitaire_estime: float = 0.0


class BCCreateRequest(BaseModel):
    type_stock: str
    fournisseur_nom: Optional[str] = None
    lignes: List[LigneBCRequest]


def _generer_numero_bc(db: Session) -> str:
    annee = datetime.utcnow().year
    count = db.query(BonCommande).filter(BonCommande.numero_bc.like(f"BC-{annee}-%")).count()
    return f"BC-{annee}-{count + 1:04d}"


@router.post("")
async def creer_bc(req: BCCreateRequest, db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    if not req.lignes:
        raise HTTPException(status_code=400, detail="error_lignes_requises")
    bc = BonCommande(
        numero_bc=_generer_numero_bc(db), type_stock=req.type_stock,
        fournisseur_nom=req.fournisseur_nom, statut="ouvert",
        cree_par_id=current_user.id, date_creation=datetime.utcnow(),
    )
    db.add(bc)
    db.flush()
    for l in req.lignes:
        db.add(LigneBonCommande(bon_commande_id=bc.id, produit_id=l.produit_id,
                                 designation=l.designation, quantite=l.quantite,
                                 prix_unitaire_estime=l.prix_unitaire_estime))
    db.commit()
    db.refresh(bc)
    await ws_manager.broadcast({"type": "bon_commande_update"})
    return _bc_to_dict(bc)


@router.get("")
def lister_bc(type_stock: Optional[str] = None, statut: str = "ouvert",
              db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(BonCommande)
    if type_stock:
        query = query.filter(BonCommande.type_stock == type_stock)
    if statut:
        query = query.filter(BonCommande.statut == statut)
    if current_user.role not in ("admin", "manager"):
        query = query.filter(BonCommande.cree_par_id == current_user.id)
    bcs = query.order_by(BonCommande.id.desc()).all()
    return {"results": [_bc_to_dict(b) for b in bcs]}


@router.get("/{bc_id}")
def get_bc(bc_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    bc = db.query(BonCommande).filter(BonCommande.id == bc_id).first()
    if not bc:
        raise HTTPException(status_code=404, detail="error_not_found")
    return _bc_to_dict(bc)


@router.put("/{bc_id}/fermer")
async def fermer_bc(bc_id: int, db: Session = Depends(get_db),
              current_user=Depends(require_role("admin", "manager"))):
    bc = db.query(BonCommande).filter(BonCommande.id == bc_id).first()
    if not bc:
        raise HTTPException(status_code=404, detail="error_not_found")
    bc.statut = "ferme"
    db.commit()
    await ws_manager.broadcast({"type": "bon_commande_update"})
    return {"status": "ok"}