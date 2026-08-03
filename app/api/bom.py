from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..core.ws_manager import ws_manager
from ..models.bom import BOM, LigneBOM, OrdreFabrication
from ..models.produits import Produit, Lot
from ..models.mouvements import Mouvement

router = APIRouter()


def _bom_to_dict(b: BOM) -> dict:
    return {
        "id": b.id, "produit_fini_id": b.produit_fini_id,
        "produit_fini_nom": b.produit_fini.nom if b.produit_fini else None,
        "nom": b.nom, "actif": bool(b.actif),
        "lignes": [
            {"id": l.id, "composant_produit_id": l.composant_produit_id,
             "composant_nom": l.composant.nom if l.composant else None,
             "composant_unite": l.composant.unite_mesure if l.composant else None,
             "quantite_necessaire": l.quantite_necessaire,
             "taux_perte": l.taux_perte or 0.0}
            for l in b.lignes
        ],
    }


class LigneBOMRequest(BaseModel):
    composant_produit_id: int
    quantite_necessaire: float
    taux_perte: float = 0.0


class BOMCreateRequest(BaseModel):
    produit_fini_id: int
    nom: str | None = None
    lignes: List[LigneBOMRequest]


@router.post("")
def creer_bom(req: BOMCreateRequest, db: Session = Depends(get_db),
              current_user=Depends(require_role("admin", "manager"))):
    if not req.lignes:
        raise HTTPException(status_code=400, detail="error_lignes_requises")
    produit = db.query(Produit).filter(Produit.id == req.produit_fini_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="error_produit_not_found")
    db.query(BOM).filter(BOM.produit_fini_id == req.produit_fini_id, BOM.actif == 1) \
        .update({"actif": 0})
    bom = BOM(produit_fini_id=req.produit_fini_id, nom=req.nom, actif=1,
              cree_par_id=current_user.id, date_creation=datetime.utcnow())
    db.add(bom)
    db.flush()
    for l in req.lignes:
        db.add(LigneBOM(bom_id=bom.id, composant_produit_id=l.composant_produit_id,
                         quantite_necessaire=l.quantite_necessaire, taux_perte=l.taux_perte))
    db.commit()
    db.refresh(bom)
    return _bom_to_dict(bom)


@router.get("")
def lister_boms(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    boms = db.query(BOM).filter(BOM.actif == 1).all()
    return {"results": [_bom_to_dict(b) for b in boms]}


@router.get("/produit/{produit_fini_id}")
def bom_du_produit(produit_fini_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    bom = db.query(BOM).filter(BOM.produit_fini_id == produit_fini_id, BOM.actif == 1).first()
    if not bom:
        raise HTTPException(status_code=404, detail="error_bom_not_found")
    return _bom_to_dict(bom)


def _besoin_reel(ligne: LigneBOM, quantite_produite: float) -> float:
    perte = (ligne.taux_perte or 0.0) / 100.0
    return ligne.quantite_necessaire * quantite_produite * (1 + perte)


def _disponible_reel(db: Session, produit_id: int) -> float:
    lots = db.query(Lot).filter(Lot.produit_id == produit_id, Lot.quantite_physique > 0).all()
    return sum(l.quantite_physique - l.quantite_reservee for l in lots)


@router.get("/{bom_id}/max-realisable")
def max_realisable(bom_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    bom = db.query(BOM).filter(BOM.id == bom_id, BOM.actif == 1).first()
    if not bom:
        raise HTTPException(status_code=404, detail="error_bom_not_found")
    if not bom.lignes:
        return {"quantite_maximale": 0, "goulot_etranglement": None}

    maximum = None
    goulot = None
    for ligne in bom.lignes:
        besoin_unitaire = _besoin_reel(ligne, 1.0)
        if besoin_unitaire <= 0:
            continue
        disponible = _disponible_reel(db, ligne.composant_produit_id)
        possible = disponible / besoin_unitaire
        if maximum is None or possible < maximum:
            maximum = possible
            goulot = ligne.composant.nom if ligne.composant else None
    return {
        "quantite_maximale": int(maximum) if maximum is not None else 0,
        "goulot_etranglement": goulot,
    }


class OFCreateRequest(BaseModel):
    bom_id: int
    quantite_produite: float
    emplacement_produit_fini: Optional[str] = None
    date_fabrication: Optional[str] = None
    date_expiration: Optional[str] = None
    numero_lot_produit_fini: Optional[str] = None


@router.post("/ordres-fabrication")
async def creer_ordre_fabrication(req: OFCreateRequest, db: Session = Depends(get_db),
                                   current_user=Depends(require_role("admin", "manager"))):
    bom = db.query(BOM).filter(BOM.id == req.bom_id, BOM.actif == 1).first()
    if not bom:
        raise HTTPException(status_code=404, detail="error_bom_not_found")
    if req.quantite_produite <= 0:
        raise HTTPException(status_code=400, detail="error_quantite_invalide")

    date_fab, date_exp = None, None
    if req.date_fabrication:
        try:
            date_fab = datetime.strptime(req.date_fabrication, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="error_date_fabrication_invalide")
    if req.date_expiration:
        try:
            date_exp = datetime.strptime(req.date_expiration, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="error_date_expiration_invalide")

    cout_total = 0.0
    consommations = []

    for ligne in bom.lignes:
        besoin = _besoin_reel(ligne, req.quantite_produite)
        disponible = _disponible_reel(db, ligne.composant_produit_id)
        if disponible < besoin:
            raise HTTPException(status_code=400,
                detail=f"error_stock_insuffisant:{ligne.composant.nom if ligne.composant else ligne.composant_produit_id}")

    numero_of = f"OF-{datetime.utcnow().strftime('%y%m%d%H%M%S')}"
    for ligne in bom.lignes:
        besoin = _besoin_reel(ligne, req.quantite_produite)
        restant = besoin
        lots = (db.query(Lot)
                .filter(Lot.produit_id == ligne.composant_produit_id, Lot.quantite_physique > 0)
                .order_by(Lot.date_expiration.asc().nullslast()).all())
        pmp_composant = ligne.composant.prix_moyen_pondere or 0.0
        for lot in lots:
            if restant <= 0:
                break
            disponible_lot = lot.quantite_physique - lot.quantite_reservee
            if disponible_lot <= 0:
                continue
            prise = min(disponible_lot, restant)
            lot.quantite_physique -= prise
            restant -= prise
            cout_total += prise * pmp_composant
            db.add(Mouvement(
                produit_id=ligne.composant_produit_id, lot_id=lot.id, type="sortie",
                quantite=int(prise), user_id=current_user.id,
                source_device="ordre_fabrication", timestamp=datetime.utcnow(),
            ))
            if lot.quantite_physique <= 0:
                from ..services.qr_print_queue_service import retirer_de_file_impression
                retirer_de_file_impression(db, lot.id)
        consommations.append({"produit_id": ligne.composant_produit_id, "quantite": besoin})

    produit_fini = bom.produit_fini
    cout_unitaire = round(cout_total / req.quantite_produite, 4) if req.quantite_produite else 0.0
    numero_lot = req.numero_lot_produit_fini or f"LOT-{numero_of}"
    lot_fini = Lot(
        produit_id=produit_fini.id, numero_lot=numero_lot,
        quantite_physique=int(req.quantite_produite), statut="disponible",
        date_entree_stock=datetime.utcnow(), emplacement=req.emplacement_produit_fini,
        date_fabrication=date_fab, date_expiration=date_exp,
    )
    db.add(lot_fini)
    db.flush()
    from ..services.qr_print_queue_service import ajouter_a_file_impression
    ajouter_a_file_impression(db, lot_fini.id)
    db.add(Mouvement(
        produit_id=produit_fini.id, lot_id=lot_fini.id, type="entree",
        quantite=int(req.quantite_produite), user_id=current_user.id,
        source_device="ordre_fabrication", timestamp=datetime.utcnow(),
    ))
    produit_fini.prix_moyen_pondere = cout_unitaire
    if not produit_fini.prix_achat:
        produit_fini.prix_achat = cout_unitaire

    of = OrdreFabrication(
        numero_of=numero_of, bom_id=bom.id, quantite_produite=req.quantite_produite,
        lot_produit_fini_id=lot_fini.id, cout_revient_total=round(cout_total, 2),
        cout_revient_unitaire=cout_unitaire, statut="termine",
        cree_par_id=current_user.id, date_creation=datetime.utcnow(),
    )
    db.add(of)
    db.commit()
    db.refresh(of)

    await ws_manager.broadcast({"type": "stock_update", "produit_id": produit_fini.id, "nouvelle_quantite": None})
    for c in consommations:
        await ws_manager.broadcast({"type": "stock_update", "produit_id": c["produit_id"], "nouvelle_quantite": None})
    await ws_manager.broadcast({"type": "qr_print_queue_update"})

    return {
        "id": of.id, "numero_of": of.numero_of, "quantite_produite": of.quantite_produite,
        "lot_produit_fini_id": lot_fini.id, "numero_lot": numero_lot,
        "cout_revient_total": of.cout_revient_total, "cout_revient_unitaire": of.cout_revient_unitaire,
    }


@router.get("/ordres-fabrication")
def lister_ordres_fabrication(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ofs = db.query(OrdreFabrication).order_by(OrdreFabrication.id.desc()).all()
    return {"results": [
        {"id": o.id, "numero_of": o.numero_of, "bom_id": o.bom_id,
         "produit_fini_nom": o.bom.produit_fini.nom if o.bom and o.bom.produit_fini else None,
         "quantite_produite": o.quantite_produite, "numero_lot": o.lot_produit_fini.numero_lot if o.lot_produit_fini else None,
         "cout_revient_total": o.cout_revient_total, "cout_revient_unitaire": o.cout_revient_unitaire,
         "date_creation": o.date_creation.isoformat() + "Z"}
        for o in ofs
    ]}