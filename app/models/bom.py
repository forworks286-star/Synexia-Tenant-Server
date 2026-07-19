from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class BOM(Base):
    """Nomenclature — la 'recette' d'un produit_fini. Une seule BOM active par produit."""
    __tablename__ = "boms"

    id = Column(Integer, primary_key=True)
    produit_fini_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    nom = Column(String, nullable=True)
    actif = Column(Integer, default=1)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_creation = Column(DateTime, nullable=True)

    produit_fini = relationship("Produit", foreign_keys=[produit_fini_id])
    lignes = relationship("LigneBOM", back_populates="bom")


class LigneBOM(Base):
    """Un composant de la recette : 'pour 1 unite de produit_fini, il faut X unite(s) de ce composant'."""
    __tablename__ = "lignes_bom"

    id = Column(Integer, primary_key=True)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    composant_produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite_necessaire = Column(Float, nullable=False)  # pour 1 unite de produit fini

    bom = relationship("BOM", back_populates="lignes")
    composant = relationship("Produit", foreign_keys=[composant_produit_id])


class OrdreFabrication(Base):
    """Execution reelle d'une BOM : 'on a produit X unites, a telle date'."""
    __tablename__ = "ordres_fabrication"

    id = Column(Integer, primary_key=True)
    numero_of = Column(String, unique=True, nullable=False)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    quantite_produite = Column(Float, nullable=False)
    lot_produit_fini_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    cout_revient_total = Column(Float, nullable=True)  # calcule automatiquement depuis le PMP des composants
    cout_revient_unitaire = Column(Float, nullable=True)
    statut = Column(String, default="termine")  # termine | annule
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_creation = Column(DateTime, nullable=False)

    bom = relationship("BOM", foreign_keys=[bom_id])
    lot_produit_fini = relationship("Lot", foreign_keys=[lot_produit_fini_id])