from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.produits import Produit, Lot
from ..models.mouvements import Mouvement
from ..models.users import User
from ..models.alertes import CommandeAuto
from ..models.tenant_config import TenantConfig
from ..services.fefo_service import verifier_fefo, FefoViolationError
from ..services.audit_service import enregistrer_audit
from ..models.factures import Facture
from ..models.lignes_facture import LigneFacture

router = APIRouter()


def _find_or_create_fournisseur(db: Session, nom: Optional[str]):
    if not nom or not nom.strip():
        return None
    from ..models.produits import Fournisseur as FournisseurModel
    f = db.query(FournisseurModel).filter(FournisseurModel.nom.ilike(nom.strip())).first()
    if f:
        return f
    f = FournisseurModel(nom=nom.strip())
    db.add(f)
    db.flush()
    return f


def _produit_to_dict(p: Produit) -> dict:
    stock_physique = sum(l.quantite_physique for l in p.lots)
    pmp = p.prix_moyen_pondere or 0.0
    return {
        "id": p.id, "sku": p.sku, "name": p.nom, "categorie": p.categorie,
        "type_stock": p.type_stock,
        "qr_reference": p.qr_code, "code_barre": p.code_barre,
        "unite_mesure": p.unite_mesure, "numero_serie": p.numero_serie,
        "photo_url": p.photo_url, "pays_origine": p.pays_origine,
        "statut_produit": p.statut_produit,
        "stock_physique": stock_physique,
        "stock_disponible": sum(l.quantite_disponible for l in p.lots),
        "stock_reserve": sum(l.quantite_reservee for l in p.lots),
        "alert_threshold": p.seuil_critique,
        "stock_securite": p.stock_securite,
        "quantite_min_commande": p.quantite_min_commande,
        "quantite_max_stock": p.quantite_max_stock,
        "prix_achat": p.prix_achat,
        "prix_moyen_pondere": pmp,
        "prix_vente": p.prix_vente,
        "taux_tva": p.taux_tva,
        "devise": p.devise,
        "valeur_stock": round(stock_physique * pmp, 2),
        "supplier_name": p.fournisseur.nom if p.fournisseur else None,
        "supplier_id": p.fournisseur_id,
        "supplier_secondaire_name": p.fournisseur_secondaire.nom if p.fournisseur_secondaire else None,
        "delai_livraison_jours": p.fournisseur.delai_livraison_jours if p.fournisseur else None,
        "champs_extra": p.champs_extra or {},
        "lots": [
            {
                "id": l.id, "numero_lot": l.numero_lot,
                "quantite_physique": l.quantite_physique,
                "quantite_disponible": l.quantite_disponible,
                "statut": l.statut, "emplacement": l.emplacement,
                "date_fabrication": str(l.date_fabrication) if l.date_fabrication else None,
                "date_expiration": str(l.date_expiration) if l.date_expiration else None,
                "temperature_requise": l.temperature_requise,
                "facture_id": l.facture_id,
                "numero_facture": l.facture.numero_facture if l.facture_id and l.facture else None,
            } for l in p.lots
        ],
    }


@router.get("/produits")
def get_produits(
    page: int = 1, limit: int = 50,
    categorie: Optional[str] = None,
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Produit).options(
        joinedload(Produit.lots),
        joinedload(Produit.fournisseur),
        joinedload(Produit.fournisseur_secondaire),
    )
    if categorie:
        query = query.filter(Produit.categorie == categorie)
    if statut:
        query = query.filter(Produit.statut_produit == statut)
    total = query.count()
    produits = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit,
            "results": [_produit_to_dict(p) for p in produits]}


@router.get("/produits/{produit_id}")
def get_produit(produit_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    p = db.query(Produit).options(
        joinedload(Produit.lots),
        joinedload(Produit.fournisseur),
        joinedload(Produit.fournisseur_secondaire),
    ).filter(Produit.id == produit_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="error_not_found")
    return _produit_to_dict(p)


class ProduitCreateRequest(BaseModel):
    sku: str
    nom: str
    categorie: Optional[str] = None
    type_stock: str = "marchandise"
    qr_code: str
    code_barre: Optional[str] = None
    unite_mesure: str = "piece"
    pays_origine: Optional[str] = None
    prix_achat: float = 0.0
    prix_moyen_pondere: float = 0.0
    prix_vente: float = 0.0
    taux_tva: float = 19.0
    devise: str = "DZD"
    seuil_critique: int = 10
    stock_securite: int = 0
    quantite_min_commande: int = 1
    fournisseur_id: Optional[int] = None
    champs_extra: dict = {}


@router.post("/produits")
async def create_produit(req: ProduitCreateRequest, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin", "manager"))):
    if db.query(Produit).filter(Produit.sku == req.sku).first():
        raise HTTPException(status_code=409, detail="error_sku_exists")
    if db.query(Produit).filter(Produit.qr_code == req.qr_code).first():
        raise HTTPException(status_code=409, detail="error_qr_exists")
    data = req.model_dump()
    if not data.get('prix_moyen_pondere') or data['prix_moyen_pondere'] == 0:
        data['prix_moyen_pondere'] = data.get('prix_achat', 0)
    p = Produit(**data, cree_par_id=current_user.id, date_creation=datetime.utcnow())
    db.add(p)
    db.commit()
    db.refresh(p)
    enregistrer_audit(db, user_id=current_user.id, action="created",
                      table_cible="produits", enregistrement_id=p.id,
                      apres=req.model_dump())
    await ws_manager.broadcast({"type": "stock_update", "produit_id": p.id, "nouvelle_quantite": 0})
    return {"status": "ok", "id": p.id}


class FournisseurCreateRequest(BaseModel):
    nom: str
    contact: Optional[str] = None
    dernier_prix: Optional[float] = None
    delai_livraison_jours: Optional[int] = None


@router.post("/fournisseurs")
def create_fournisseur(req: FournisseurCreateRequest, db: Session = Depends(get_db),
                       current_user=Depends(require_role("admin"))):
    from ..models.produits import Fournisseur as FournisseurModel
    f = FournisseurModel(
        nom=req.nom, contact=req.contact,
        dernier_prix=req.dernier_prix,
        delai_livraison_jours=req.delai_livraison_jours,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"status": "ok", "id": f.id, "nom": f.nom}


class LotCreateRequest(BaseModel):
    produit_id: int
    numero_lot: Optional[str] = None
    quantite_physique: int = 0
    quantite_reservee: int = 0
    statut: str = "disponible"
    emplacement: Optional[str] = None


@router.post("/lots")
async def create_lot(req: LotCreateRequest, db: Session = Depends(get_db),
               current_user=Depends(require_role("admin"))):
    lot = Lot(
        produit_id=req.produit_id,
        numero_lot=req.numero_lot or f"LOT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        quantite_physique=req.quantite_physique,
        quantite_reservee=req.quantite_reservee,
        statut=req.statut,
        emplacement=req.emplacement,
        date_entree_stock=datetime.utcnow(),
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    await ws_manager.broadcast({"type": "stock_update", "produit_id": req.produit_id, "nouvelle_quantite": lot.quantite_physique})

    return {"status": "ok", "id": lot.id}


class ProduitUpdateRequest(BaseModel):
    nom: Optional[str] = None
    categorie: Optional[str] = None
    prix_achat: Optional[float] = None
    prix_vente: Optional[float] = None
    prix_moyen_pondere: Optional[float] = None
    taux_tva: Optional[float] = None
    seuil_critique: Optional[int] = None
    stock_securite: Optional[int] = None
    statut_produit: Optional[str] = None
    pays_origine: Optional[str] = None
    fournisseur_id: Optional[int] = None
    fournisseur_secondaire_id: Optional[int] = None
    champs_extra: Optional[dict] = None


@router.put("/produits/{produit_id}")
def update_produit(produit_id: int, req: ProduitUpdateRequest,
                   db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin", "manager"))):
    p = db.query(Produit).filter(Produit.id == produit_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="error_not_found")
    avant = {"nom": p.nom, "prix_achat": p.prix_achat, "statut_produit": p.statut_produit}
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    p.modifie_par_id = current_user.id
    p.date_derniere_modification = datetime.utcnow()
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="updated",
                      table_cible="produits", enregistrement_id=p.id,
                      avant=avant, apres=req.model_dump(exclude_none=True))
    return {"status": "ok"}


@router.post("/scan")
def scan_produit(data: dict, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    p = db.query(Produit).options(joinedload(Produit.lots)).filter(
        Produit.qr_code == data.get("qr_code", "")
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="error_not_found")
    return {
        "id": p.id, "sku": p.sku, "nom": p.nom, "qr_code": p.qr_code,
        "champs_extra": p.champs_extra or {},
        "lots": [
            {
                "id": l.id, "numero_lot": l.numero_lot,
                "quantite_physique": l.quantite_physique,
                "quantite_disponible": l.quantite_disponible,
                "statut": l.statut, "emplacement": l.emplacement,
                "date_expiration": str(l.date_expiration) if l.date_expiration else None,
            } for l in p.lots if l.quantite_physique > 0
        ],
    }


class MouvementRequest(BaseModel):
    produit_id: int
    lot_id: int
    type: str
    quantite: int
    photo_preuve_url: Optional[str] = None
    numero_commande_achat: Optional[str] = None
    numero_bl: Optional[str] = None
    source_device: str = "mobile"


@router.post("/mouvements")
async def enregistrer_mouvement(req: MouvementRequest, db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    config = db.query(TenantConfig).first()
    if config and config.module_photo_obligatoire and not req.photo_preuve_url:
        raise HTTPException(status_code=400, detail="error_photo_required")
    if req.type == "sortie":
        try:
            verifier_fefo(db, req.produit_id, req.lot_id, config)
        except FefoViolationError as e:
            raise HTTPException(status_code=409, detail={
                "message": "error_fefo_violation",
                "lot_correct_id": e.lot_correct.id,
                "emplacement": e.lot_correct.emplacement,
            })
    lot = db.query(Lot).filter(Lot.id == req.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="error_lot_not_found")
    if req.type == "sortie" and lot.quantite_disponible < req.quantite:
        raise HTTPException(status_code=400, detail="error_insufficient_stock")
    avant = lot.quantite_physique
    if req.type in ("entree", "retour"):
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
        user_id=current_user.id, source_device=req.source_device,
        timestamp=datetime.utcnow(), synced=True,
    )
    db.add(mouvement)
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="mouvement_stock",
                      table_cible="lots", enregistrement_id=lot.id,
                      avant={"quantite_physique": avant},
                      apres={"quantite_physique": lot.quantite_physique},
                      source_device=req.source_device)
    await ws_manager.broadcast({
        "type": "stock_update",
        "produit_id": req.produit_id,
        "nouvelle_quantite": lot.quantite_physique,
    })
    return {"status": "ok", "nouvelle_quantite_lot": lot.quantite_physique}


@router.get("/mouvements")
def get_mouvements(
    page: int = 1, limit: int = 50,
    produit_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Mouvement).options(
        joinedload(Mouvement.produit)
    ).order_by(Mouvement.timestamp.desc())
    if produit_id:
        query = query.filter(Mouvement.produit_id == produit_id)
    total = query.count()
    mouvements = query.offset((page - 1) * limit).limit(limit).all()
    users = {u.id: u.full_name for u in db.query(User).all()}
    return {
        "total": total, "page": page, "limit": limit,
        "results": [
            {
                "id": m.id, "product_id": m.produit_id,
                "product_name": m.produit.nom if m.produit else "",
                "type": "entry" if m.type == "entree" else ("return" if m.type == "retour" else "exit"),
                "quantity": m.quantite,
                "numero_commande_achat": m.numero_commande_achat,
                "numero_bl": m.numero_bl,
                "photo_preuve_url": m.photo_preuve_url,
                "date": str(m.timestamp),
                "user_name": users.get(m.user_id, ""),
            } for m in mouvements
        ],
    }


@router.get("/alertes-stock")
async def get_alertes_stock(db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    from ..services.alertes_service import creer_alerte
    produits = db.query(Produit).options(
        joinedload(Produit.lots), joinedload(Produit.fournisseur)
    ).all()
    critiques = []
    for p in produits:
        stock_total = sum(l.quantite_physique for l in p.lots)
        if stock_total <= p.seuil_critique:
            existe = db.query(CommandeAuto).filter(
                CommandeAuto.produit_id == p.id,
                CommandeAuto.statut == "pending"
            ).first()
            if not existe:
                commande = CommandeAuto(
                    produit_id=p.id, sku=p.sku, designation=p.nom,
                    quantite_suggeree=max(p.quantite_min_commande, p.seuil_critique * 2),
                    fournisseur_nom=p.fournisseur.nom if p.fournisseur else "",
                    fournisseur_id=p.fournisseur_id,
                    dernier_prix_achat=p.prix_achat,
                    timestamp=datetime.utcnow(),
                )
                db.add(commande)
                db.commit()
                await creer_alerte(
                    db, type="stock", niveau="warning",
                    message=f"Commande auto generee — {p.nom}",
                    source="stock",
                    meta={"produit_id": p.id, "commande_id": commande.id},
                )
            critiques.append({
                "produit_id": p.id, "sku": p.sku, "nom": p.nom,
                "stock_actuel": stock_total, "seuil_critique": p.seuil_critique,
                "fournisseur": p.fournisseur.nom if p.fournisseur else None,
                "commande_auto_pending": True,
            })
    return {"results": critiques}


@router.get("/commandes-auto")
def get_commandes_auto(db: Session = Depends(get_db),
                       current_user=Depends(require_role("admin", "manager"))):
    commandes = db.query(CommandeAuto).filter(
        CommandeAuto.statut == "pending"
    ).order_by(CommandeAuto.timestamp.desc()).all()
    return {"results": [
        {
            "id": c.id, "sku": c.sku, "designation": c.designation,
            "quantite_suggeree": c.quantite_suggeree,
            "fournisseur_nom": c.fournisseur_nom,
            "dernier_prix_achat": c.dernier_prix_achat,
            "timestamp": str(c.timestamp),
        } for c in commandes
    ]}


@router.put("/commandes-auto/{commande_id}/valider")
def valider_commande(commande_id: int, db: Session = Depends(get_db),
                     current_user=Depends(require_role("admin", "manager"))):
    c = db.query(CommandeAuto).filter(CommandeAuto.id == commande_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="error_not_found")
    c.statut = "validated"
    c.validee_par_id = current_user.id
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="commande_validee",
                      table_cible="commandes_auto", enregistrement_id=c.id)
    return {"status": "ok"}


@router.put("/commandes-auto/{commande_id}/rejeter")
def rejeter_commande(commande_id: int, db: Session = Depends(get_db),
                     current_user=Depends(require_role("admin", "manager"))):
    c = db.query(CommandeAuto).filter(CommandeAuto.id == commande_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="error_not_found")
    c.statut = "rejected"
    c.validee_par_id = current_user.id
    db.commit()
    enregistrer_audit(db, user_id=current_user.id, action="commande_rejetee",
                      table_cible="commandes_auto", enregistrement_id=c.id)
    return {"status": "ok"}


class AjoutManuelCompletRequest(BaseModel):
    sku: str
    nom: str
    categorie: Optional[str] = None
    qr_code: str
    code_barre: Optional[str] = None
    unite_mesure: str = "piece"
    type_stock: str = "marchandise"
    prix_achat: float = 0.0
    prix_vente: float = 0.0
    taux_tva: float = 19.0
    devise: str = "DZD"
    seuil_critique: int = 10
    quantite_initiale: int
    date_expiration: Optional[str] = None
    fournisseur_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    pays_origine: Optional[str] = None
    fournisseur_nif: Optional[str] = None
    fournisseur_nis: Optional[str] = None
    fournisseur_rc: Optional[str] = None


@router.post("/produits/ajout-manuel-complet")
async def ajout_manuel_complet(req: AjoutManuelCompletRequest, db: Session = Depends(get_db),
                                current_user=Depends(require_role("admin", "manager"))):
    from ..services.alertes_service import creer_alerte
    from .integrations import _generate_numero_facture

    if db.query(Produit).filter(Produit.sku == req.sku).first():
        raise HTTPException(status_code=409, detail="error_sku_exists")
    if db.query(Produit).filter(Produit.qr_code == req.qr_code).first():
        raise HTTPException(status_code=409, detail="error_qr_exists")

    fournisseur = _find_or_create_fournisseur(db, req.fournisseur_nom)

    produit = Produit(
        sku=req.sku, nom=req.nom, categorie=req.categorie, qr_code=req.qr_code,
        code_barre=req.code_barre, unite_mesure=req.unite_mesure,
        type_stock=req.type_stock, prix_achat=req.prix_achat,
        prix_moyen_pondere=req.prix_achat, prix_vente=req.prix_vente,
        taux_tva=req.taux_tva, devise=req.devise, seuil_critique=req.seuil_critique,
        pays_origine=req.pays_origine,
        fournisseur_id=fournisseur.id if fournisseur else req.fournisseur_id,
        cree_par_id=current_user.id, date_creation=datetime.utcnow(),
    )
    db.add(produit)
    db.flush()

    montant_ht = round(req.quantite_initiale * req.prix_achat, 2)
    montant_tva = round(montant_ht * req.taux_tva / 100, 2)
    montant_ttc = round(montant_ht + montant_tva, 2)

    facture = Facture(
        fournisseur_nom=req.fournisseur_nom or "Ajustement manuel (stock initial)",
        date=datetime.utcnow().date(), type_facture="ajustement_manuel",
        montant_ht=montant_ht, montant_tva=montant_tva, montant_ttc=montant_ttc,
        taux_tva=req.taux_tva, numero_facture=_generate_numero_facture(db),
        fournisseur_nif=req.fournisseur_nif, fournisseur_nis=req.fournisseur_nis,
        fournisseur_rc=req.fournisseur_rc,
        statut="validated", cree_manuellement=True,
    )
    
    db.add(facture)
    db.flush()

    db.add(LigneFacture(
        facture_id=facture.id, produit_id=produit.id,
        designation_brute=produit.nom, quantite=req.quantite_initiale,
        prix_unitaire=req.prix_achat, montant_ligne=montant_ht, source="manuel",
    ))

    lot = Lot(
        produit_id=produit.id, numero_lot=f"LOT-{facture.numero_facture}-A",
        quantite_physique=req.quantite_initiale, statut="disponible",
        date_entree_stock=datetime.utcnow(), facture_id=facture.id,
        date_expiration=req.date_expiration,
    )
    db.add(lot)
    db.flush()
    db.add(Mouvement(
        produit_id=produit.id, lot_id=lot.id, type="entree",
        quantite=req.quantite_initiale, user_id=current_user.id,
        source_device="ajustement_manuel", timestamp=datetime.utcnow(),
    ))
    db.commit()
    db.refresh(produit)

    await creer_alerte(
        db, type="stock", niveau="info",
        message=f"Produit '{produit.nom}' ajoute manuellement — stock initial {req.quantite_initiale} unites (Facture {facture.numero_facture})",
        source="manuel", meta={"produit_id": produit.id, "facture_id": facture.id},
    )
    await ws_manager.broadcast({"type": "stock_update", "produit_id": produit.id, "nouvelle_quantite": req.quantite_initiale})
    await ws_manager.broadcast({
        "type": "new_facture", "id": facture.id,
        "fournisseur_nom": facture.fournisseur_nom, "montant_ttc": facture.montant_ttc,
        "incoherence_detectee": False,
    })

    return {"status": "ok", "produit_id": produit.id, "facture_id": facture.id}