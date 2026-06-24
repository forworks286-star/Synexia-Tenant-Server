from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DEVICE_API_KEY: str = ""

    LICENSE_KEY: str = ""
    LICENSE_SERVER_URL: str = "https://license.synexia.dz"
    LICENSE_CHECK_INTERVAL_HOURS: int = 24

    TENANT_NAME: str = "Mon Entrepot"
    TENANT_TYPE: str = "generic"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    class Config:
        env_file = ".env"


settings = Settings()

if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL manquant dans .env — demarrage refuse")
if not settings.SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquant dans .env — demarrage refuse")
if not settings.DEVICE_API_KEY:
    raise RuntimeError("DEVICE_API_KEY manquant dans .env — demarrage refuse")
