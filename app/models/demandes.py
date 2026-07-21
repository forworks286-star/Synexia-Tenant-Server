from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class DemandeModification(Base):
    __tablename__ = "demandes_modification"

    id = Column(Integer, primary_key=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False)
    demandeur_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    compte_rendu = Column(String, nullable=False)

    statut = Column(String, default="pending")  # pending | approuvee | refusee
    traite_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    motif_refus = Column(String, nullable=True)

    date_creation = Column(DateTime, nullable=False)
    date_traitement = Column(DateTime, nullable=True)

    facture = relationship("Facture", foreign_keys=[facture_id])
    demandeur = relationship("User", foreign_keys=[demandeur_id])