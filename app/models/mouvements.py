from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from ..core.database import Base

class Mouvement(Base):
    """
    كل حركة دخول/خروج - تشمل دعم Offline-first عبر synced
    """
    __tablename__ = "mouvements"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    type = Column(String, nullable=False)  # entree | sortie
    quantite = Column(Integer, nullable=False)

    photo_preuve_url = Column(String, nullable=True)  # إلزامي حسب tenant_config
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_device = Column(String, nullable=True)  # kiosk | mobile | desktop

    timestamp = Column(DateTime, nullable=False)
    synced = Column(Boolean, default=True)  # false = جاء من جهاز كان Offline وتمت مزامنته بعدها

    # حقل ثابت غير قابل للتعديل لاحقاً - جاهز لمتطلبات Cyber (immutable logs)
    log_hash = Column(String, nullable=True)
