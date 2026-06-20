from sqlalchemy import Column, Integer, String, DateTime, JSON
from ..core.database import Base

class AuditLog(Base):
    """
    Journal immuable - aucune mise à jour ni suppression autorisée par le code applicatif
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)  # created | updated | deleted | login | login_failed
    table_cible = Column(String, nullable=False)
    enregistrement_id = Column(Integer, nullable=True)
    valeur_avant = Column(JSON, nullable=True)
    valeur_apres = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    source_device = Column(String, nullable=True)
