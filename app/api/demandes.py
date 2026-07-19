from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.demandes import DemandeModification
from ..models.factures import Facture
from ..models.lignes_facture import LigneFacture
from ..services.audit_service import enregistrer_audit
from ..services.alertes_service import creer_alerte

router = APIRouter()

# champs qu'une demande de modification peut cibler
CHAMPS_FACTURE = {"fournisseur_nom", "montant_ht", "montant_tva", "montant_ttc", "date"}


def _demande_to_dict(d: DemandeModification) -> dict:
    return {
        "id": d.id, "facture_id": d.facture_id, "demandeur_id": d.demandeur_id,
        "champ_concerne": d.champ_concerne,
        "valeur_actuelle": d.valeur_actuelle, "valeur_proposee": d.valeur_proposee,
        "compte_rendu": d.compte_rendu, "statut": d.statut,
        "traite_par_id": d.traite_par_id, "motif_refus": d.motif_refus,
        "date_creation": d.date_creation.isoformat() + "Z",
        "date_traitement": d.date_traitement.isoformat() + "Z" if d.date_traitement else None,
    }


class DemandeCreateRequest(BaseModel):
    facture_id: int
    champ_concerne: str  # ex: "montant_ht" ou "ligne:12:quantite" ou "ligne:12:date_expiration"
    valeur_proposee: str
    compte_rendu: str


@router.post("/modification")
async def creer_demande(req: DemandeCreateRequest, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    if not req.compte_rendu or not req.compte_rendu.strip():
        raise HTTPException(status_code=400, detail="error_compte_rendu_requis")
    facture = db.query(Facture).filter(Facture.id == req.facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_facture_not_found")
    if current_user.role not in ("admin", "manager") and facture.cree_par_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_facture_pas_a_vous")

    valeur_actuelle = None
    est_date_expiration = req.champ_concerne.endswith(":date_expiration")

    if req.champ_concerne.startswith("ligne:"):
        _, ligne_id, champ = req.champ_concerne.split(":")
        ligne = db.query(LigneFacture).filter(LigneFacture.id == int(ligne_id)).first()
        if not ligne:
            raise HTTPException(status_code=404, detail="error_ligne_not_found")
        valeur_actuelle = str(getattr(ligne, champ, ""))
    elif req.champ_concerne in CHAMPS_FACTURE:
        valeur_actuelle = str(getattr(facture, req.champ_concerne, ""))
    else:
        raise HTTPException(status_code=400, detail="error_champ_invalide")

    demande = DemandeModification(
        facture_id=req.facture_id, demandeur_id=current_user.id,
        champ_concerne=req.champ_concerne, valeur_actuelle=valeur_actuelle,
        valeur_proposee=req.valeur_proposee, compte_rendu=req.compte_rendu.strip(),
        statut="pending", date_creation=datetime.utcnow(),
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)

    # Exception convenue : uniquement date d'expiration manquante/erronee -> le Lot reste
    # utilisable immediatement (pas de blocage stock), mais la demande est quand meme creee
    # et une alerte complete est envoyee pour tracabilite.
    niveau = "info" if est_date_expiration else "warning"
    message = (
        f"Demande de modification (date d'expiration) — {current_user.full_name} — "
        f"utilisable immediatement en attendant validation"
        if est_date_expiration else
        f"Demande de modification — {current_user.full_name} — facture #{req.facture_id} verrouillee"
    )
    await creer_alerte(
        db, type="demande_modification", niveau=niveau, message=message,
        source="demandes",
        meta={"demande_id": demande.id, "facture_id": req.facture_id,
              "champ": req.champ_concerne, "immediat": est_date_expiration},
    )
    await ws_manager.broadcast({"type": "demande_update", "id": demande.id, "statut": "pending"})
    return _demande_to_dict(demande)


@router.get("/modification")
def lister_demandes(statut: str = "pending", db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    query = db.query(DemandeModification)
    if statut:
        query = query.filter(DemandeModification.statut == statut)
    if current_user.role not in ("admin", "manager"):
        query = query.filter(DemandeModification.demandeur_id == current_user.id)
    demandes = query.order_by(DemandeModification.id.desc()).all()
    return {"results": [_demande_to_dict(d) for d in demandes]}


class TraiterRequest(BaseModel):
    motif_refus: str | None = None


@router.put("/modification/{demande_id}/approuver")
async def approuver_demande(demande_id: int, db: Session = Depends(get_db),
                             current_user=Depends(require_role("admin", "manager"))):
    demande = db.query(DemandeModification).filter(DemandeModification.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="error_not_found")
    if demande.statut != "pending":
        raise HTTPException(status_code=400, detail="error_demande_deja_traitee")

    facture = db.query(Facture).filter(Facture.id == demande.facture_id).first()
    if demande.champ_concerne.startswith("ligne:"):
        _, ligne_id, champ = demande.champ_concerne.split(":")
        ligne = db.query(LigneFacture).filter(LigneFacture.id == int(ligne_id)).first()
        if not ligne:
            raise HTTPException(status_code=404, detail="error_ligne_not_found")
        if champ == "date_expiration_manquante":
            setattr(ligne, champ, "false")
        else:
            setattr(ligne, champ, demande.valeur_proposee)
        if champ == "date_expiration":
            ligne.date_expiration_manquante = "false"
    else:
        setattr(facture, demande.champ_concerne, demande.valeur_proposee)

    demande.statut = "approuvee"
    demande.traite_par_id = current_user.id
    demande.date_traitement = datetime.utcnow()
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="demande_approuvee",
                      table_cible="demandes_modification", enregistrement_id=demande.id)
    await ws_manager.broadcast({"type": "demande_update", "id": demande.id, "statut": "approuvee"})
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": demande.facture_id})
    return {"status": "ok"}


@router.put("/modification/{demande_id}/refuser")
async def refuser_demande(demande_id: int, req: TraiterRequest, db: Session = Depends(get_db),
                           current_user=Depends(require_role("admin", "manager"))):
    demande = db.query(DemandeModification).filter(DemandeModification.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="error_not_found")
    if demande.statut != "pending":
        raise HTTPException(status_code=400, detail="error_demande_deja_traitee")
    demande.statut = "refusee"
    demande.motif_refus = req.motif_refus
    demande.traite_par_id = current_user.id
    demande.date_traitement = datetime.utcnow()
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="demande_refusee",
                      table_cible="demandes_modification", enregistrement_id=demande.id)
    await ws_manager.broadcast({"type": "demande_update", "id": demande.id, "statut": "refusee"})
    return {"status": "ok"}