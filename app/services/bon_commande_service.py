from sqlalchemy.orm import Session

from ..models.bon_commande import BonCommande


def liberer_bon_commande_si_lie(db: Session, facture) -> bool:
   
    if not facture.bon_commande_id:
        return False

    bc = db.query(BonCommande).filter(
        BonCommande.id == facture.bon_commande_id,
        BonCommande.statut == "recu",
    ).first()
    if not bc:
        return False

    bc.statut = "ouvert"
    bc.reserve_par_id = None
    return True