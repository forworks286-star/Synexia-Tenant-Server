from sqlalchemy.orm import Session
from datetime import date
from ..models.produits import Lot

class FefoViolationError(Exception):
    """Levée quand l'agent tente de prélever sur un mauvais lot"""
    def __init__(self, lot_correct: Lot):
        self.lot_correct = lot_correct
        super().__init__("FEFO violation")

def verifier_fefo(db: Session, produit_id: int, lot_id_demande: int, tenant_config) -> None:
    """
    Appelée avant chaque sortie de stock - uniquement si module_fefo est activé.
    Refuse le prélèvement sur un lot éloigné s'il existe un lot avec une date plus proche.
    """
    if not tenant_config.module_fefo:
        return  # L'entrepôt n'utilise pas FEFO (pièces détachées par exemple) - aucune contrainte

    lots_disponibles = (
    db.query(Lot)
    .filter(Lot.produit_id == produit_id, Lot.quantite_physique > 0, Lot.date_expiration.isnot(None))
    .order_by(Lot.date_expiration.asc())
    .all()
)

    if not lots_disponibles:
        return  # Aucun lot avec date de péremption pour ce produit

    lot_correct = lots_disponibles[0]  # Le lot le plus proche doit être prélevé en premier

    if lot_correct.id != lot_id_demande:
        raise FefoViolationError(lot_correct)
