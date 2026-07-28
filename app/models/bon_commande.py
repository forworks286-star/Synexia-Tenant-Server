from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class BonCommande(Base):
    __tablename__ = "bons_commande"

    id = Column(Integer, primary_key=True)
    numero_bc = Column(String, unique=True, nullable=False)
    type_stock = Column(String, nullable=False)
    fournisseur_nom = Column(String, nullable=True)
    statut = Column(String, default="ouvert")  # ouvert | en_cours | recu | ferme
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reserve_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_creation = Column(DateTime, nullable=False)

    lignes = relationship("LigneBonCommande", back_populates="bon_commande", cascade="all, delete-orphan")
    createur = relationship("User", foreign_keys=[cree_par_id])


class LigneBonCommande(Base):
    __tablename__ = "lignes_bon_commande"

    id = Column(Integer, primary_key=True)
    bon_commande_id = Column(Integer, ForeignKey("bons_commande.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=True)
    designation = Column(String, nullable=False)
    quantite = Column(Float, nullable=False)
    prix_unitaire_estime = Column(Float, default=0.0)

    bon_commande = relationship("BonCommande", back_populates="lignes")
    produit = relationship("Produit", foreign_keys=[produit_id])