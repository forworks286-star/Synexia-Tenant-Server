from sqlalchemy import Column, Integer, String, JSON, DateTime
from ..core.database import Base


class IoTZoneState(Base):
    __tablename__ = "iot_zone_states"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    profil = Column(String, nullable=False)
    valeurs = Column(JSON, default=dict)
    derniere_maj = Column(DateTime, nullable=True)


class IoTZoneEvenement(Base):
    __tablename__ = "iot_zone_evenements"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, nullable=False)
    niveau = Column(String, nullable=False)
    libelle = Column(String, nullable=False)
    valeurs = Column(JSON, default=dict)
    date_creation = Column(DateTime, nullable=False)