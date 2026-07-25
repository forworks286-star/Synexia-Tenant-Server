from sqlalchemy.orm import Session
from ..models.bon_commande import BonCommande


def comparer_avec_bc(db: Session, bon_commande: BonCommande, lignes_facture: list, fournisseur_nom: str = None) -> list:
    ecarts = []
    lignes_bc_traitees = set()

    if bon_commande.fournisseur_nom and fournisseur_nom:
        if bon_commande.fournisseur_nom.strip().lower() != fournisseur_nom.strip().lower():
            ecarts.append({"type": "fournisseur_different",
                            "commande": bon_commande.fournisseur_nom, "recu": fournisseur_nom})

    for lf in lignes_facture:
        if isinstance(lf, dict):
            designation = lf.get("designation") or ""
            produit_id = lf.get("produit_id")
            quantite = lf.get("quantite")
            prix = lf.get("prix_unitaire")
        else:
            designation = lf.designation_brute or ""
            produit_id = lf.produit_id
            quantite = lf.quantite
            prix = lf.prix_unitaire
        ligne_bc = None
        for l in bon_commande.lignes:
            if l.id in lignes_bc_traitees:
                continue
            if produit_id and l.produit_id and produit_id == l.produit_id:
                ligne_bc = l
                break
            if l.designation.strip().lower() == (designation or "").strip().lower():
                ligne_bc = l
                break

        if not ligne_bc:
            ecarts.append({"type": "produit_non_commande", "designation": designation,
                            "quantite_recue": quantite, "prix_recu": prix})
            continue

        lignes_bc_traitees.add(ligne_bc.id)
        diff = {}
        if quantite is not None and round(quantite, 3) != round(ligne_bc.quantite, 3):
            diff["quantite"] = {"commandee": ligne_bc.quantite, "recue": quantite}
        if prix is not None and ligne_bc.prix_unitaire_estime and round(prix, 2) != round(ligne_bc.prix_unitaire_estime, 2):
            diff["prix_unitaire"] = {"estime": ligne_bc.prix_unitaire_estime, "recu": prix}
        if diff:
            ecarts.append({"type": "ecart", "designation": designation, **diff})

    for l in bon_commande.lignes:
        if l.id not in lignes_bc_traitees:
            ecarts.append({"type": "produit_manquant", "designation": l.designation,
                            "quantite_commandee": l.quantite})

    return ecarts