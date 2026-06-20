from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from ..core.database import Base


class Mouvement(Base):
    __tablename__ = "mouvements"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)

    type = Column(String, nullable=False)  # entree | sortie | retour

    quantite = Column(Integer, nullable=False)

    numero_commande_achat = Column(String, nullable=True)
    numero_bl = Column(String, nullable=True)

    photo_preuve_url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_device = Column(String, nullable=True)

    timestamp = Column(DateTime, nullable=False)
    synced = Column(Boolean, default=True)
    log_hash = Column(String, nullable=True)
