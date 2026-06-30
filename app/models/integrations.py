from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from ..core.database import Base


class CameraEvent(Base):
    """Rempli par l'équipe IA/Vision via API."""
    __tablename__ = "camera_events"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    video_clip_url = Column(String, nullable=True)
    personne_id = Column(String, nullable=True)
    personne_nom = Column(String, nullable=True)
    confiance = Column(String, nullable=True)
    raw_data = Column(JSON, default=dict)


class FaceEvent(Base):
    """Rempli par l'équipe IA — Face Recognition / Access Control."""
    __tablename__ = "face_events"

    id = Column(Integer, primary_key=True)
    personne_id = Column(String, nullable=True)
    nom = Column(String, nullable=True)
    reconnu = Column(Boolean, default=False)
    confiance = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    methode = Column(String, default="face_id")
    autorise = Column(Boolean, default=False)
    timestamp = Column(DateTime, nullable=False)
    raw_data = Column(JSON, default=dict)


class AutomationEvent(Base):
    """
    Rempli par l'équipe Automatique — un seul payload complet par appareil PLC.
    Structure conforme au schema JSON fourni par l'équipe (header/inputs/outputs/...).
    """
    __tablename__ = "automation_events"

    id = Column(Integer, primary_key=True)

    # Identification (depuis payload.header)
    device_id = Column(String, nullable=False, index=True)
    device_name = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    controller_brand = Column(String, nullable=True)
    controller_model = Column(String, nullable=True)
    module = Column(String, nullable=False, index=True)  # SmartLighting | HVAC | FireSystem | ...
    site_id = Column(String, nullable=True)
    warehouse_id = Column(String, nullable=True)
    zone_id = Column(String, nullable=True, index=True)
    line_id = Column(String, nullable=True)

    # Payload complet tel que reçu (inputs, outputs, states, lighting, hvac,
    # energy, iot, maintenance, diagnostic, alarms, events)
    payload = Column(JSON, nullable=False, default=dict)

    has_alarm = Column(Boolean, default=False)
    timestamp = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)


class EnergieLog(Base):
    """Conservé pour compatibilité — historique simplifié de consommation."""
    __tablename__ = "energie_logs"

    id = Column(Integer, primary_key=True)
    zone = Column(String, nullable=False)
    consommation_kwh = Column(String, nullable=False)
    mode = Column(String, default="normal")
    timestamp = Column(DateTime, nullable=False)
    raw_data = Column(JSON, default=dict)