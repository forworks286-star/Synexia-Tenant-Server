from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from ..core.database import Base


class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    dernier_prix = Column(Float, nullable=True)


class Produit(Base):
    __tablename__ = "produits"

    id = Column(Integer, primary_key=True)

    # Identification (Master Data - Niveau 1)
    sku = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    categorie = Column(String, nullable=True)
    qr_code = Column(String, unique=True, nullable=False)
    code_barre = Column(String, nullable=True)
    unite_mesure = Column(String, default="piece")

    seuil_critique = Column(Integer, default=10)
    prix_achat = Column(Float, default=0.0)
    prix_vente = Column(Float, default=0.0)

    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)
    champs_extra = Column(JSON, default=dict)

    lots = relationship("Lot", back_populates="produit")
    fournisseur = relationship("Fournisseur")


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite = Column(Integer, default=0)
    date_expiration = Column(Date, nullable=True)
    emplacement = Column(String, nullable=True)
    temperature_requise = Column(String, nullable=True)

    produit = relationship("Produit", back_populates="lots")
