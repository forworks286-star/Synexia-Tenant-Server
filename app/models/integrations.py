from sqlalchemy import Column, Integer, String, DateTime, JSON
from ..core.database import Base

class CameraEvent(Base):
    """
    Rempli par l'équipe IA/Vision via API - nous ne générons pas ces données
    """
    __tablename__ = "camera_events"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String, nullable=False)
    type = Column(String, nullable=False)  # anomalie | intrusion | objet_verrouille
    zone = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    video_clip_url = Column(String, nullable=True)
    raw_data = Column(JSON, default=dict)  # flexible pour tout format envoyé par l'équipe IA


class EnergieLog(Base):
    """
    Rempli par l'équipe Automatique/IoT via API
    """
    __tablename__ = "energie_logs"

    id = Column(Integer, primary_key=True)
    zone = Column(String, nullable=False)
    consommation_kwh = Column(String, nullable=False)
    mode = Column(String, default="normal")  # eco | normal
    timestamp = Column(DateTime, nullable=False)
    raw_data = Column(JSON, default=dict)
