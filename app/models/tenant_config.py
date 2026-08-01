from sqlalchemy import Column, Integer, String, Boolean, JSON
from ..core.database import Base

class TenantConfig(Base):
    """
    Configuration exacte de cet entrepôt - une seule ligne dans cette table.
    Modifier une valeur ici active/désactive une fonctionnalité sans toucher au code.
    """
    __tablename__ = "tenant_config"

    id = Column(Integer, primary_key=True, default=1)
    tenant_name = Column(String, default="Mon Entrepôt")
    tenant_type = Column(String, default="generic")  

 
    module_fefo = Column(Boolean, default=False)             
    module_temperature = Column(Boolean, default=False)      
    module_photo_obligatoire = Column(Boolean, default=True)  
    module_qr_obligatoire = Column(Boolean, default=True)    


    module_camera_security = Column(Boolean, default=False)  
    module_iot_energie = Column(Boolean, default=False)      
    module_ocr_factures = Column(Boolean, default=True)      


    champs_produit_extra = Column(JSON, default=dict)

    workflow_validation = Column(JSON, default=lambda: ["qr", "photo"])
