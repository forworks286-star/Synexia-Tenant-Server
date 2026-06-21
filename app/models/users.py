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
    password_hash = Column(String, nullable=False)  # bcrypt - prêt à être remplacé par le standard Cyber

    role = Column(String, nullable=False)  # admin | manager | stockiste | agent_kiosk
    # Permissions fines en plus du rôle de base - flexibilité totale pour Cyber
    permissions = Column(JSON, default=list)  # exemple: ["valider_facture", "modifier_stock", "voir_camera"]

    pin_code_hash = Column(String, nullable=True)      # connexion Kiosk par PIN
    face_id_hash = Column(String, nullable=True)        # empreinte faciale (emplacement prêt pour Cyber)
    biometric_enabled = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)

    # Champ prêt pour chiffrement AES-256 ultérieur par l'équipe Cyber (données sensibles)
    encrypted_metadata = Column(String, nullable=True)
