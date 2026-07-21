from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require_role
from ..core.ws_manager import ws_manager
from ..models.demandes import DemandeModification
from ..models.factures import Facture
from ..services.audit_service import enregistrer_audit
from ..services.alertes_service import creer_alerte

router = APIRouter()


def _demande_to_dict(d: DemandeModification) -> dict:
    return {
        "id": d.id, "facture_id": d.facture_id, "demandeur_id": d.demandeur_id,
        "demandeur_nom": d.demandeur.full_name if d.demandeur else None,
        "compte_rendu": d.compte_rendu, "statut": d.statut,
        "traite_par_id": d.traite_par_id, "motif_refus": d.motif_refus,
        "date_creation": d.date_creation.isoformat() + "Z",
        "date_traitement": d.date_traitement.isoformat() + "Z" if d.date_traitement else None,
        "facture_fournisseur": d.facture.fournisseur_nom if d.facture else None,
        "facture_montant_ttc": d.facture.montant_ttc if d.facture else None,
    }


@router.get("/modification")
def lister_demandes(statut: str = "pending", db: Session = Depends(get_db),
                     current_user=Depends(require_role("admin", "manager"))):
    demandes = db.query(DemandeModification).filter(
        DemandeModification.statut == statut
    ).order_by(DemandeModification.id.desc()).all()
    return {"results": [_demande_to_dict(d) for d in demandes]}


@router.put("/modification/{demande_id}/approuver")
async def approuver_demande(demande_id: int, db: Session = Depends(get_db),
                             current_user=Depends(require_role("admin", "manager"))):
    demande = db.query(DemandeModification).filter(DemandeModification.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="error_not_found")
    if demande.statut != "pending":
        raise HTTPException(status_code=400, detail="error_demande_deja_traitee")

    facture = db.query(Facture).filter(Facture.id == demande.facture_id).first()
    if not facture or facture.statut != "en_attente_modification":
        raise HTTPException(status_code=400, detail="error_facture_invalide")

    facture.statut = "modification_autorisee"
    demande.statut = "approuvee"
    demande.traite_par_id = current_user.id
    demande.date_traitement = datetime.utcnow()
    db.commit()

    enregistrer_audit(db, user_id=current_user.id, action="demande_approuvee",
                      table_cible="demandes_modification", enregistrement_id=demande.id)
    await creer_alerte(
        db, type="demande_modification", niveau="info",
        message=f"Votre demande de modification sur la facture #{facture.id} a ete acceptee — vous pouvez la completer",
        source="demandes", meta={"facture_id": facture.id, "demande_id": demande.id},
        destinataire_id=demande.demandeur_id,
    )
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": facture.id})
    return {"status": "ok"}


class RefuserBody(BaseModel):
    motif_refus: str


@router.put("/modification/{demande_id}/refuser")
async def refuser_demande(demande_id: int, req: RefuserBody, db: Session = Depends(get_db),
                           current_user=Depends(require_role("admin", "manager"))):
    demande = db.query(DemandeModification).filter(DemandeModification.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="error_not_found")
    if demande.statut != "pending":
        raise HTTPException(status_code=400, detail="error_demande_deja_traitee")

    facture = db.query(Facture).filter(Facture.id == demande.facture_id).first()
    if facture:
        facture.statut = "rejected"
        facture.motif_rejet = f"Demande de modification refusee : {req.motif_refus}"

    demande.statut = "refusee"
    demande.motif_refus = req.motif_refus
    demande.traite_par_id = current_user.id
    demande.date_traitement = datetime.utcnow()
    db.commit()

    enregistrer_audit(db, user_id=current_user.id, action="demande_refusee",
                      table_cible="demandes_modification", enregistrement_id=demande.id)
    await creer_alerte(
        db, type="demande_modification", niveau="danger",
        message=f"Votre demande de modification sur la facture #{demande.facture_id} a ete refusee : {req.motif_refus}",
        source="demandes", meta={"facture_id": demande.facture_id, "demande_id": demande.id},
        destinataire_id=demande.demandeur_id,
    )
    return {"status": "ok"}