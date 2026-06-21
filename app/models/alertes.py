from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from ..core.database import Base

class Alerte(Base):
    """
    Table unifiée pour tous les types d'alertes quelle que soit la source.
    source_module indique l'origine: nous, IA, ou IoT.
    """
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)  # stock | securite | energie
    niveau = Column(String, default="info")  # info | warning | danger | success
    message = Column(String, nullable=False)

    source_module = Column(String, nullable=False)  # stock_app | ia_vision | iot_automatique
    metadata_json = Column(JSON, default=dict)  # données additionnelles selon la source (exemple video_clip_url)

    timestamp = Column(DateTime, nullable=False)
    lu = Column(Boolean, default=False)


class CommandeAuto(Base):
    """Réapprovisionnement intelligent"""
    __tablename__ = "commandes_auto"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, nullable=False)
    quantite_suggeree = Column(Integer, nullable=False)
    statut = Column(String, default="en_attente")  # en_attente | validee | rejetee
    timestamp = Column(DateTime, nullable=False)
