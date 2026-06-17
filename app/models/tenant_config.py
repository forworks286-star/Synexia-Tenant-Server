from sqlalchemy import Column, Integer, String, Boolean, JSON
from ..core.database import Base

class TenantConfig(Base):
    """
    إعدادات هذا المستودع بالضبط - صف واحد فقط في هذا الجدول
    تغيير أي قيمة هنا يفعّل/يعطّل ميزة بدون تعديل أي كود
    """
    __tablename__ = "tenant_config"

    id = Column(Integer, primary_key=True, default=1)
    tenant_name = Column(String, default="Mon Entrepôt")
    tenant_type = Column(String, default="generic")  # generic | pharmacie | supermarche | pieces_detachees

    # Modules قابلة للتفعيل (Module 1 - Stock)
    module_fefo = Column(Boolean, default=False)              # ترتيب السحب حسب تاريخ الانتهاء
    module_temperature = Column(Boolean, default=False)       # تتبع درجة الحرارة
    module_photo_obligatoire = Column(Boolean, default=True)  # صورة إلزامية عند كل حركة
    module_qr_obligatoire = Column(Boolean, default=True)     # مسح QR إلزامي (لا بحث نصي)

    # Modules القادمة من باقي الفريق (تُفعَّل حسب الكراسة)
    module_camera_security = Column(Boolean, default=False)   # Pôle IA/Vision
    module_iot_energie = Column(Boolean, default=False)       # Pôle Automatique/IoT
    module_ocr_factures = Column(Boolean, default=True)       # Pôle IA - OCR

    # حقول مخصصة لكل نوع مستودع (مرونة كاملة - JSON ديناميكي)
    # مثال صيدلية: {"numero_lot_medicament": "text", "ordonnance_requise": "boolean"}
    # مثال قطع غيار: {"reference_constructeur": "text", "poids_kg": "number"}
    champs_produit_extra = Column(JSON, default=dict)

    # ترتيب خطوات التحقق الإلزامية قبل تأكيد أي حركة مخزون
    workflow_validation = Column(JSON, default=lambda: ["qr", "photo"])
