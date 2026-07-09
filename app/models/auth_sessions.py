from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from ..core.database import Base


class RefreshSession(Base):
    """
    Un seul enregistrement par session de connexion active (un par device/login).
    current_jti est écrasé (UPDATE) à chaque rotation — jamais d'accumulation.
    """
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_jti = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)