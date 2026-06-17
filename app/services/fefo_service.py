from sqlalchemy.orm import Session
from datetime import date
from ..models.produits import Lot

class FefoViolationError(Exception):
    """يُرفع حين يحاول العامل سحب من دفعة خاطئة"""
    def __init__(self, lot_correct: Lot):
        self.lot_correct = lot_correct
        super().__init__("FEFO violation")

def verifier_fefo(db: Session, produit_id: int, lot_id_demande: int, tenant_config) -> None:
    """
    يُستدعى قبل كل سحب من المخزون - إذا كان module_fefo مفعّل فقط
    يرفض السحب من دفعة بعيدة إذا توجد دفعة أقرب انتهاءً
    """
    if not tenant_config.module_fefo:
        return  # المستودع لا يستخدم FEFO (قطع غيار مثلاً) - لا قيد

    lots_disponibles = (
        db.query(Lot)
        .filter(Lot.produit_id == produit_id, Lot.quantite > 0, Lot.date_expiration.isnot(None))
        .order_by(Lot.date_expiration.asc())
        .all()
    )

    if not lots_disponibles:
        return  # لا توجد دفعات بتاريخ انتهاء لهذا المنتج

    lot_correct = lots_disponibles[0]  # الأقرب انتهاءً يجب أن يُسحب أولاً

    if lot_correct.id != lot_id_demande:
        raise FefoViolationError(lot_correct)
