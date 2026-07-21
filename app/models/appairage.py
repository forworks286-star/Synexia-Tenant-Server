from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class SessionAppairage(Base):
    """Code/QR temporaire a usage unique reliant une session Logiciel a une
    application mobile externe pour recevoir le resultat d'un OCR a distance."""
    __tablename__ = "sessions_appairage"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type_stock = Column(String, nullable=False)
    type_facture = Column(String, default="achat")
    statut = Column(String, default="attente")  # attente | scanne | complete | expire
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=True)
    date_creation = Column(DateTime, nullable=False)
    date_expiration = Column(DateTime, nullable=False)

    createur = relationship("User", foreign_keys=[cree_par_id])
    facture = relationship("Facture", foreign_keys=[facture_id])