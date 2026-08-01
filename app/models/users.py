from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from ..core.database import Base

class User(Base):
    """
    Système de permissions flexible - nombre de rôles illimité, chaque rôle porte une liste de permissions.
    L'équipe Cyber-Sécurité peut ajouter de nouvelles permissions sans modifier la structure de la table.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False) 

    role = Column(String, nullable=False) 
    
    permissions = Column(JSON, default=list)  

    pin_code_hash = Column(String, nullable=True)     
    face_id_hash = Column(String, nullable=True)      
    biometric_enabled = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)

  
    encrypted_metadata = Column(String, nullable=True)
