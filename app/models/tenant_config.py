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
    tenant_type = Column(String, default="generic")  # generic | pharmacie | supermarche | pieces_detachees

    # Modules activables (Module 1 - Stock)
    module_fefo = Column(Boolean, default=False)              # ordre de prélèvement par date de péremption
    module_temperature = Column(Boolean, default=False)       # suivi de la température
    module_photo_obligatoire = Column(Boolean, default=True)  # photo obligatoire à chaque mouvement
    module_qr_obligatoire = Column(Boolean, default=True)     # scan QR obligatoire (pas de recherche texte)

    # Modules à venir des autres équipes (activés selon le cahier des charges)
    module_camera_security = Column(Boolean, default=False)   # Pôle IA/Vision
    module_iot_energie = Column(Boolean, default=False)       # Pôle Automatique/IoT
    module_ocr_factures = Column(Boolean, default=True)       # Pôle IA - OCR

    # Champs personnalisés selon le type d'entrepôt (flexibilité totale - JSON dynamique)
    # exemple pharmacie: {"numero_lot_medicament": "text", "ordonnance_requise": "boolean"}
    # exemple pièces détachées: {"reference_constructeur": "text", "poids_kg": "number"}
    champs_produit_extra = Column(JSON, default=dict)

    # Ordre des étapes de validation obligatoires avant confirmation d'un mouvement de stock
    workflow_validation = Column(JSON, default=lambda: ["qr", "photo"])
