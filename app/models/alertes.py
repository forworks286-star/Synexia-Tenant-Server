from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, ForeignKey
from ..core.database import Base


class Alerte(Base):
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    niveau = Column(String, default="info")
    message = Column(String, nullable=False)
    source_module = Column(String, nullable=False)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, nullable=False)
    lu = Column(Boolean, default=False)
    destinataire_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class AlerteLue(Base):
    __tablename__ = "alertes_lues"

    id = Column(Integer, primary_key=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_lecture = Column(DateTime, nullable=False)


class CommandeAuto(Base):
    __tablename__ = "commandes_auto"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    sku = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    quantite_suggeree = Column(Integer, nullable=False)
    fournisseur_nom = Column(String, nullable=True)
    fournisseur_id = Column(Integer, nullable=True)
    dernier_prix_achat = Column(Float, nullable=True)
    statut = Column(String, default="pending")
    cree_par = Column(String, default="system")
    timestamp = Column(DateTime, nullable=False)
    validee_par_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
