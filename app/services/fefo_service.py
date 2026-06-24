from sqlalchemy.orm import Session
from datetime import date
from ..models.produits import Lot


class FefoViolationError(Exception):
    """Raised when an agent tries to pick from the wrong batch (FEFO violation)."""
    def __init__(self, lot_correct: Lot):
        self.lot_correct = lot_correct
        super().__init__("FEFO violation")


def verifier_fefo(db: Session, produit_id: int, lot_id_demande: int, tenant_config) -> None:
    """
    Called before every stock exit — only if module_fefo is enabled.
    Rejects pick from a distant batch if a closer expiry batch exists.
    """
    if not tenant_config or not tenant_config.module_fefo:
        return

    lots_disponibles = (
        db.query(Lot)
        .filter(Lot.produit_id == produit_id,
                Lot.quantite_physique > 0,
                Lot.date_expiration.isnot(None))
        .order_by(Lot.date_expiration.asc())
        .all()
    )

    if not lots_disponibles:
        return

    lot_correct = lots_disponibles[0]
    if lot_correct.id != lot_id_demande:
        raise FefoViolationError(lot_correct)
