from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.factures import Facture
from ..models.lignes_facture import LigneFacture
from ..services.audit_service import enregistrer_audit
from ..services.stock_service import appliquer_lignes_facture
from ..services.bon_commande_service import liberer_bon_commande_si_lie

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
        "a_ete_modifiee": f.a_ete_modifiee,
        "bon_commande_id": f.bon_commande_id,
        "ecarts_bc": f.ecarts_bc,
        "ecart_compte_rendu": f.ecart_compte_rendu,
        "stamp_detected": True, "signature_detected": True,
    }


@router.get("")
def get_factures(page: int = 1, limit: int = 50, type_facture: Optional[str] = None,
                 statut: Optional[str] = None,
                 db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Facture)
    if type_facture:
        query = query.filter(Facture.type_facture == type_facture)
    STATUTS_PERSONNELS = ("ocr_a_verifier", "modification_autorisee", "ecart_a_signaler")
    if statut:
        query = query.filter(Facture.statut == statut)
    else:
        query = query.filter(Facture.statut.notin_(["en_attente_modification", "modification_autorisee", "ocr_a_verifier", "ecart_a_signaler", "ecart_a_valider"]))
    if current_user.role not in ("admin", "manager") or statut in STATUTS_PERSONNELS:
        query = query.filter(Facture.cree_par_id == current_user.id)
    total = query.count()
    factures = query.order_by(Facture.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit,
            "results": [_facture_to_dict(f) for f in factures]}


class LigneManuelleRequest(BaseModel):
    produit_id: Optional[int] = None
    designation: Optional[str] = None
    quantite: float
    prix_unitaire: float
    prix_vente: Optional[float] = None
    date_fabrication: Optional[str] = None
    date_expiration: Optional[str] = None
    numero_lot_fournisseur: Optional[str] = None
    nouveau_categorie: Optional[str] = None
    nouveau_code_barre: Optional[str] = None
    nouveau_unite_mesure: Optional[str] = None
    nouveau_seuil_critique: Optional[int] = None
    nouveau_emplacement: Optional[str] = None


class FactureManuelleRequest(BaseModel):
    fournisseur_nom: str
    date: str
    type_facture: str = "achat"  
    type_stock: str  
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    taux_tva: float = 19.0
    fournisseur_nif: Optional[str] = None
    fournisseur_nis: Optional[str] = None
    fournisseur_rc: Optional[str] = None
    motif_creation_manuelle: str
    lignes: List[LigneManuelleRequest] = []
    compte_rendu_demande: Optional[str] = None
    bon_commande_id: Optional[int] = None

@router.post("/manuelle")
async def creer_facture_manuelle(req: FactureManuelleRequest, db: Session = Depends(get_db),
                                  current_user=Depends(get_current_user)):
    if not req.motif_creation_manuelle or not req.motif_creation_manuelle.strip():
        raise HTTPException(status_code=400, detail="error_motif_requis")
    if not req.lignes:
        raise HTTPException(status_code=400, detail="error_lignes_requises")
    from ..api.integrations import _generate_numero_facture
    from ..services.stock_service import trouver_produit_correspondant
    try:
        date_facture = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="error_date_invalide")

    facture = Facture(
        fournisseur_nom=req.fournisseur_nom, date=date_facture,
        montant_ht=req.montant_ht, montant_tva=req.montant_tva, montant_ttc=req.montant_ttc,
        taux_tva=req.taux_tva, numero_facture=_generate_numero_facture(db),
        fournisseur_nif=req.fournisseur_nif, fournisseur_nis=req.fournisseur_nis,
        fournisseur_rc=req.fournisseur_rc,
        type_facture=req.type_facture, type_stock=req.type_stock,
        statut="en_attente_modification" if req.compte_rendu_demande else "pending",
        cree_manuellement=True, motif_creation_manuelle=req.motif_creation_manuelle.strip(),
        cree_par_id=current_user.id,
    )
    db.add(facture)
    db.flush()

    date_manquante_globale = False
    for l in req.lignes:
        produit_id = l.produit_id
        if not produit_id and l.designation:
            trouve = trouver_produit_correspondant(db, l.designation)
            if trouve:
                produit_id = trouve.id
        date_manquante = req.type_facture != "vente" and not l.date_expiration
        if date_manquante:
            date_manquante_globale = True
        db.add(LigneFacture(
            facture_id=facture.id, produit_id=produit_id,
            designation_brute=l.designation, type_stock=req.type_stock,
            quantite=l.quantite, prix_unitaire=l.prix_unitaire, prix_vente=l.prix_vente,
            date_fabrication=l.date_fabrication, date_expiration=l.date_expiration,
            date_expiration_manquante="true" if date_manquante else "false",
            numero_lot_fournisseur=l.numero_lot_fournisseur,
            nouveau_categorie=l.nouveau_categorie, nouveau_code_barre=l.nouveau_code_barre,
            nouveau_unite_mesure=l.nouveau_unite_mesure, nouveau_seuil_critique=l.nouveau_seuil_critique,
            nouveau_emplacement=l.nouveau_emplacement,
            montant_ligne=round(l.quantite * l.prix_unitaire, 2), source="manuel",
        ))
    db.commit()
    db.refresh(facture)

    if req.bon_commande_id:
        from ..models.bon_commande import BonCommande
        from sqlalchemy import or_  
        from ..services.comparaison_bc import comparer_avec_bc
        
       
        claim = db.query(BonCommande).filter(
            BonCommande.id == req.bon_commande_id,
            BonCommande.statut.in_(["ouvert", "en_cours"]),  
            or_(
                BonCommande.reserve_par_id.is_(None),  
                BonCommande.reserve_par_id == current_user.id  
            )
        ).update({"statut": "recu"})
        db.commit()
        
        if claim == 0:
            raise HTTPException(status_code=409, detail="error_bon_commande_deja_utilise")
        
        
        bc = db.query(BonCommande).filter(BonCommande.id == req.bon_commande_id).first()
        if bc:
            lignes_crees = db.query(LigneFacture).filter(LigneFacture.facture_id == facture.id).all()
            ecarts = comparer_avec_bc(db, bc, lignes_crees, fournisseur_nom=facture.fournisseur_nom)
            facture.bon_commande_id = bc.id
            if ecarts:
                facture.statut_apres_ecart = facture.statut
                facture.ecarts_bc = ecarts
                facture.statut = "ecart_a_signaler"
        
        await ws_manager.broadcast({"type": "bon_commande_update"})

    enregistrer_audit(db, user_id=current_user.id, action="facture_creee_manuellement",
                      table_cible="factures", enregistrement_id=facture.id,
                      apres={"motif": req.motif_creation_manuelle, "nb_lignes": len(req.lignes)})
    from ..services.alertes_service import notifier_admins
    await notifier_admins(
        db, type="facture", niveau="warning",
        message=f"Facture creee manuellement par {current_user.full_name} — verification requise",
        source="facture_manuelle",
        meta={"facture_id": facture.id, "user_id": current_user.id},
    )
    if date_manquante_globale:
        await notifier_admins(
            db, type="facture", niveau="warning",
            message=f"Date(s) d'expiration manquante(s) sur la facture manuelle #{facture.id}",
            source="facture_manuelle",
            meta={"facture_id": facture.id},
        )
    if req.compte_rendu_demande:
        from ..models.demandes import DemandeModification
        db.add(DemandeModification(
            facture_id=facture.id, demandeur_id=current_user.id,
            compte_rendu=req.compte_rendu_demande.strip(),
            statut="pending", date_creation=datetime.utcnow(),
        ))
        db.commit()
        await notifier_admins(
            db, type="demande_modification", niveau="warning",
            message=f"Nouvelle demande de modification — {current_user.full_name} — facture #{facture.id}",
            source="demandes", meta={"facture_id": facture.id},
        )
    await ws_manager.broadcast({
        "type": "new_facture", "id": facture.id,
        "fournisseur_nom": req.fournisseur_nom, "montant_ttc": req.montant_ttc,
        "cree_manuellement": True,
    })
    return _facture_to_dict(facture)


class CompleterModificationRequest(BaseModel):
    fournisseur_nom: str
    date: str
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    taux_tva: float = 19.0
    lignes: List[LigneManuelleRequest] = []


@router.put("/{facture_id}/completer-modification")
async def completer_modification(facture_id: int, req: CompleterModificationRequest,
                                   db: Session = Depends(get_db),
                                   current_user=Depends(get_current_user)):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.cree_par_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_facture_pas_a_vous")
    if facture.statut != "modification_autorisee":
        raise HTTPException(status_code=400, detail="error_facture_pas_en_modification")

    try:
        date_facture = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="error_date_invalide")

    from ..services.stock_service import trouver_produit_correspondant
    db.query(LigneFacture).filter(LigneFacture.facture_id == facture_id).delete()

    facture.fournisseur_nom = req.fournisseur_nom
    facture.date = date_facture
    facture.montant_ht = req.montant_ht
    facture.montant_tva = req.montant_tva
    facture.montant_ttc = req.montant_ttc
    facture.taux_tva = req.taux_tva
    facture.statut = "pending"
    facture.a_ete_modifiee = True

    for l in req.lignes:
        produit_id = l.produit_id
        if not produit_id and l.designation:
            trouve = trouver_produit_correspondant(db, l.designation)
            if trouve:
                produit_id = trouve.id
        db.add(LigneFacture(
            facture_id=facture.id, produit_id=produit_id,
            designation_brute=l.designation, type_stock=facture.type_stock,
            quantite=l.quantite, prix_unitaire=l.prix_unitaire, prix_vente=l.prix_vente,
            date_fabrication=l.date_fabrication, date_expiration=l.date_expiration,
            date_expiration_manquante="false" if l.date_expiration else "true",
            numero_lot_fournisseur=l.numero_lot_fournisseur,
            montant_ligne=round(l.quantite * l.prix_unitaire, 2), source="manuel",
        ))
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_modification_completee",
                      table_cible="factures", enregistrement_id=facture.id)
    await ws_manager.broadcast({"type": "new_facture", "id": facture.id, "cree_manuellement": True})
    return _facture_to_dict(facture)


class LigneConfirmationOcr(BaseModel):
    id: int
    emplacement: Optional[str] = None
    nouveau_categorie: Optional[str] = None
    nouveau_code_barre: Optional[str] = None
    nouveau_unite_mesure: Optional[str] = None
    nouveau_seuil_critique: Optional[int] = None


class ConfirmerOcrRequest(BaseModel):
    lignes: List[LigneConfirmationOcr] = []


@router.put("/{facture_id}/emplacements-ocr")
async def enregistrer_emplacements_ocr(facture_id: int, req: ConfirmerOcrRequest, db: Session = Depends(get_db),
                                        current_user=Depends(get_current_user)):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.cree_par_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_facture_pas_a_vous")
    if facture.statut not in ("ocr_a_verifier", "en_attente_modification", "modification_autorisee"):
        raise HTTPException(status_code=400, detail="error_facture_invalide")

    for l in req.lignes:
        ligne = db.query(LigneFacture).filter(LigneFacture.id == l.id, LigneFacture.facture_id == facture_id).first()
        if not ligne:
            continue
        if l.emplacement is not None:
            ligne.nouveau_emplacement = l.emplacement
        if not ligne.produit_id:
            if l.nouveau_categorie is not None:
                ligne.nouveau_categorie = l.nouveau_categorie
            if l.nouveau_code_barre is not None:
                ligne.nouveau_code_barre = l.nouveau_code_barre
            if l.nouveau_unite_mesure is not None:
                ligne.nouveau_unite_mesure = l.nouveau_unite_mesure
            if l.nouveau_seuil_critique is not None:
                ligne.nouveau_seuil_critique = l.nouveau_seuil_critique

    db.commit()
    return {"status": "ok"}

@router.put("/{facture_id}/confirmer-ocr")
async def confirmer_ocr(facture_id: int, req: ConfirmerOcrRequest, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.cree_par_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_facture_pas_a_vous")
    if facture.statut != "ocr_a_verifier":
        raise HTTPException(status_code=400, detail="error_facture_pas_en_verification")

    for l in req.lignes:
        ligne = db.query(LigneFacture).filter(LigneFacture.id == l.id, LigneFacture.facture_id == facture_id).first()
        if not ligne:
            continue
        if l.emplacement is not None:
            ligne.nouveau_emplacement = l.emplacement
        if not ligne.produit_id:
            if l.nouveau_categorie is not None:
                ligne.nouveau_categorie = l.nouveau_categorie
            if l.nouveau_code_barre is not None:
                ligne.nouveau_code_barre = l.nouveau_code_barre
            if l.nouveau_unite_mesure is not None:
                ligne.nouveau_unite_mesure = l.nouveau_unite_mesure
            if l.nouveau_seuil_critique is not None:
                ligne.nouveau_seuil_critique = l.nouveau_seuil_critique

    facture.statut = "pending"
    db.commit()
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": facture.id})
    return {"status": "ok"}

class EnvoyerEcartRequest(BaseModel):
    compte_rendu: str


@router.put("/{facture_id}/envoyer-ecart")
async def envoyer_ecart(facture_id: int, req: EnvoyerEcartRequest, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.cree_par_id != current_user.id:
        raise HTTPException(status_code=403, detail="error_facture_pas_a_vous")
    if facture.statut != "ecart_a_signaler":
        raise HTTPException(status_code=400, detail="error_facture_invalide")
    if not req.compte_rendu or not req.compte_rendu.strip():
        raise HTTPException(status_code=400, detail="error_compte_rendu_requis")

    facture.ecart_compte_rendu = req.compte_rendu.strip()
    facture.statut = "ecart_a_valider"
    db.commit()
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": facture.id})
    from ..services.alertes_service import notifier_admins
    await notifier_admins(
        db, type="ecart_bc", niveau="warning",
        message=f"Écart bon de commande signalé par {current_user.full_name} — facture #{facture.id}",
        source="bons_commande", meta={"facture_id": facture.id},
    )
    return {"status": "ok"}


@router.put("/{facture_id}/approuver-ecart")
async def approuver_ecart(facture_id: int, db: Session = Depends(get_db),
                           current_user=Depends(require_role("admin", "manager"))):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.statut != "ecart_a_valider":
        raise HTTPException(status_code=400, detail="error_facture_invalide")
    facture.statut = facture.statut_apres_ecart or "pending"
    db.commit()
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": facture.id})
    return {"status": "ok"}


@router.put("/{facture_id}/rejeter-ecart")
async def rejeter_ecart(facture_id: int, db: Session = Depends(get_db),
                         current_user=Depends(require_role("admin", "manager"))):
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="error_not_found")
    if facture.statut != "ecart_a_valider":
        raise HTTPException(status_code=400, detail="error_facture_invalide")
    facture.statut = "annulee"

    from ..models.demandes import DemandeModification
    demande_liee = db.query(DemandeModification).filter(
        DemandeModification.facture_id == facture.id, DemandeModification.statut == "pending"
    ).first()
    if demande_liee:
        demande_liee.statut = "refuse"
        demande_liee.motif_refus = "Facture annulée suite au rejet de l'écart bon de commande"
        demande_liee.traite_par_id = current_user.id
        demande_liee.date_traitement = datetime.utcnow()

    bc_libere = liberer_bon_commande_si_lie(db, facture)

    db.commit()
    await ws_manager.broadcast({"type": "facture_draft_update", "facture_id": facture.id})
    await ws_manager.broadcast({"type": "demande_update"})
    if bc_libere:
        await ws_manager.broadcast({"type": "bon_commande_update"})
    return {"status": "ok"}

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
    await ws_manager.broadcast({"type": "qr_print_queue_update"})
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

    bc_libere = liberer_bon_commande_si_lie(db, f)

    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="facture_rejetee",
                      table_cible="factures", enregistrement_id=f.id, apres={"motif": req.motif})
    await ws_manager.broadcast({"type": "facture_update", "id": f.id, "status": "rejected"})
    if bc_libere:
        await ws_manager.broadcast({"type": "bon_commande_update"})
    return {"status": "ok"}