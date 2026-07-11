import re
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.produits import Produit, Lot
from ..models.factures import Facture
from ..models.mouvements import Mouvement


def _normaliser(nom: str) -> str:
    n = nom.strip().lower()
    return re.sub(r"\s+", " ", n)


def _extraire_nombres(nom: str) -> list:
    return re.findall(r"\d+", nom)


def trouver_produit_correspondant(db: Session, designation: str):
    """Matching strict : ignore casse/espaces, mais tous les nombres doivent
    correspondre exactement (500mg != 1000mg -> produits différents)."""
    if not designation:
        return None
    cible_norm = _normaliser(designation)
    cible_nombres = _extraire_nombres(designation)
    candidats = db.query(Produit).filter(Produit.statut_produit == "actif").all()
    for p in candidats:
        if _extraire_nombres(p.nom) != cible_nombres:
            continue
        p_norm = _normaliser(p.nom)
        if cible_norm in p_norm or p_norm in cible_norm:
            return p
    return None


def _generer_sku(nom: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]", "", nom or "PROD").upper()[:10] or "PROD"
    return f"{base}-{datetime.utcnow().strftime('%y%m%d%H%M%S')}"


def appliquer_lignes_facture(db: Session, facture: Facture, lignes: list, current_user):
    """Appelée uniquement à la validation d'une facture.
    achat/ajustement_manuel -> crée un Lot par ligne (entrée), crée le Produit si absent.
    vente -> décrémente les lots existants en respectant FEFO."""
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    est_sortie = facture.type_facture == "vente"

    for idx, ligne in enumerate(lignes):
        produit = None
        if ligne.produit_id:
            produit = db.query(Produit).filter(Produit.id == ligne.produit_id).first()
        if not produit:
            produit = trouver_produit_correspondant(db, ligne.designation_brute)

        if not produit:
            if est_sortie:
                raise HTTPException(status_code=400,
                    detail=f"error_produit_introuvable_vente:{ligne.designation_brute}")
            if not ligne.type_stock:
                raise HTTPException(status_code=400,
                    detail=f"error_type_stock_requis:{ligne.designation_brute}")
            sku = _generer_sku(ligne.designation_brute)
            produit = Produit(
                sku=sku, nom=ligne.designation_brute or "Produit sans nom",
                qr_code=f"QR-{sku}", type_stock=ligne.type_stock,
                prix_achat=ligne.prix_unitaire, prix_moyen_pondere=ligne.prix_unitaire,
                prix_vente=ligne.prix_unitaire,
                cree_par_id=current_user.id, date_creation=datetime.utcnow(),
            )
            db.add(produit)
            db.flush()

        ligne.produit_id = produit.id

        if not est_sortie:
            numero_lot = f"LOT-{facture.numero_facture or facture.id}-{lettres[idx % 26]}"
            lot = Lot(
                produit_id=produit.id, numero_lot=numero_lot,
                quantite_physique=int(ligne.quantite), statut="disponible",
                date_entree_stock=datetime.utcnow(), facture_id=facture.id,
            )
            db.add(lot)
            db.flush()
            db.add(Mouvement(
                produit_id=produit.id, lot_id=lot.id, type="entree",
                quantite=int(ligne.quantite), user_id=current_user.id,
                source_device="facture", timestamp=datetime.utcnow(),
            ))
        else:
            qte_restante = int(ligne.quantite)
            lots = (db.query(Lot)
                    .filter(Lot.produit_id == produit.id, Lot.quantite_physique > 0)
                    .order_by(Lot.date_expiration.asc().nullslast()).all())
            if sum(l.quantite_physique for l in lots) < qte_restante:
                raise HTTPException(status_code=400,
                    detail=f"error_stock_insuffisant:{produit.nom}")
            for lot in lots:
                if qte_restante <= 0:
                    break
                prise = min(lot.quantite_physique, qte_restante)
                lot.quantite_physique -= prise
                qte_restante -= prise
                db.add(Mouvement(
                    produit_id=produit.id, lot_id=lot.id, type="sortie",
                    quantite=prise, user_id=current_user.id,
                    source_device="facture", timestamp=datetime.utcnow(),
                ))