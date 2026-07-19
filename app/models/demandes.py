from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class DemandeModification(Base):
    """
    Une demande = une facture verrouillee en attente d'arbitrage admin.
    champ_concerne: nom du champ ou 'ligne:<id>' ou 'facture' (global).
    """
    __tablename__ = "demandes_modification"

    id = Column(Integer, primary_key=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False)
    demandeur_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    champ_concerne = Column(String, nullable=False)
    valeur_actuelle = Column(String, nullable=True)
    valeur_proposee = Column(String, nullable=True)
    compte_rendu = Column(String, nullable=False)  # motif obligatoire ecrit par le demandeur

    statut = Column(String, default="pending")  # pending | approuvee | refusee
    traite_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    motif_refus = Column(String, nullable=True)

    date_creation = Column(DateTime, nullable=False)
    date_traitement = Column(DateTime, nullable=True)

    facture = relationship("Facture", foreign_keys=[facture_id])