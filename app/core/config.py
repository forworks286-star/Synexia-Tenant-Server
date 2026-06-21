from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Base de données
    DATABASE_URL: str = "postgresql://synexia:synexia1234@localhost:5432/synexia_db"

    # Sécurité (sera remplacé par les clés de l'équipe Cyber-Sécurité plus tard)
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Licence — se connecte à notre serveur pour vérification
    LICENSE_KEY: str = ""
    LICENSE_SERVER_URL: str = "https://license.synexia.dz"
    LICENSE_CHECK_INTERVAL_HOURS: int = 24

    # Informations de ce client (Tenant)
    TENANT_NAME: str = "Mon Entrepôt"
    TENANT_TYPE: str = "generic"  # generic | pharmacie | supermarche | pieces_detachees

    class Config:
        env_file = ".env"

settings = Settings()
