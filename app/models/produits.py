from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base

class Produit(Base):
    __tablename__ = "produits"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    qr_code = Column(String, unique=True, nullable=False)
    seuil_critique = Column(Integer, default=10)
    prix_achat = Column(Float, default=0.0)
    prix_vente = Column(Float, default=0.0)
    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)

    # حقول مخصصة حسب نوع المستودع (يقرأها التطبيق من tenant_config.champs_produit_extra)
    champs_extra = Column(JSON, default=dict)

    lots = relationship("Lot", back_populates="produit")
    fournisseur = relationship("Fournisseur")

class Lot(Base):
    """
    دفعة واحدة من منتج - أساس خوارزمية FEFO
    منتج واحد قد يملك عدة دفعات بتواريخ انتهاء مختلفة
    """
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite = Column(Integer, default=0)
    date_expiration = Column(Date, nullable=True)  # NULL = منتج بدون تاريخ انتهاء (قطع غيار مثلاً)
    emplacement = Column(String, nullable=True)    # "Allée 3, Rack B"
    temperature_requise = Column(String, nullable=True)  # "2-8°C" - للأدوية فقط

    produit = relationship("Produit", back_populates="lots")

class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    dernier_prix = Column(Float, nullable=True)
