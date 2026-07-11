from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base


class LigneFacture(Base):
    __tablename__ = "lignes_facture"

    id = Column(Integer, primary_key=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=True)
    designation_brute = Column(String, nullable=True)
    type_stock = Column(String, nullable=True)
    quantite = Column(Float, default=0.0)
    prix_unitaire = Column(Float, default=0.0)
    montant_ligne = Column(Float, default=0.0)
    source = Column(String, default="manuel")  # manuel | ocr
    raw_json = Column(JSON, default=dict)

    facture = relationship("Facture", foreign_keys=[facture_id])
    produit = relationship("Produit", foreign_keys=[produit_id])