from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # قاعدة البيانات
    DATABASE_URL: str = "postgresql://synexia:synexia123@localhost:5432/synexia_db"

    # الأمان (سيُستبدل بمفاتيح فريق Cyber-Sécurité لاحقاً)
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # الترخيص — يتصل بسيرفرنا للتحقق
    LICENSE_KEY: str = ""
    LICENSE_SERVER_URL: str = "https://license.synexia.dz"
    LICENSE_CHECK_INTERVAL_HOURS: int = 24

    # معلومات هذا الزبون (Tenant)
    TENANT_NAME: str = "Mon Entrepôt"
    TENANT_TYPE: str = "generic"  # generic | pharmacie | supermarche | pieces_detachees

    class Config:
        env_file = ".env"

settings = Settings()
