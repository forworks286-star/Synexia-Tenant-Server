from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from ..core.database import Base

class User(Base):
    """
    نظام صلاحيات مرن - عدد الأدوار غير محدود، وكل دور يحمل قائمة صلاحيات
    فريق Cyber-Sécurité يمكنه إضافة صلاحيات جديدة هنا بدون تعديل بنية الجدول
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # bcrypt - جاهز ليُستبدل بمعيار Cyber الخاص

    role = Column(String, nullable=False)  # admin | manager | stockiste | agent_kiosk
    # صلاحيات دقيقة إضافية فوق الدور الأساسي - مرونة كاملة لـ Cyber
    permissions = Column(JSON, default=list)  # مثال: ["valider_facture", "modifier_stock", "voir_camera"]

    pin_code_hash = Column(String, nullable=True)      # دخول الـ Kiosk بـ PIN
    face_id_hash = Column(String, nullable=True)        # بصمة وجه (مكان جاهز لفريق Cyber)
    biometric_enabled = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)

    # حقل جاهز لتشفير AES-256 لاحقاً من فريق Cyber (مثلاً تشفير البيانات الحساسة)
    encrypted_metadata = Column(String, nullable=True)
