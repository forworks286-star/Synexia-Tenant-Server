from app.core.database import SessionLocal
from app.models.users import User
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

# احذف المستخدم القديم إن وجد
db.query(User).filter(User.username == "saadi").delete()
db.commit()

admin = User(
    full_name="Saadi Dadi",
    username="saadi",
    password_hash=pwd_context.hash("Dadi"),
    role="admin",
    permissions=["valider_facture", "modifier_stock", "voir_camera", "gerer_utilisateurs"],
    is_active=True,
    created_at=datetime.utcnow()
)
db.add(admin)
db.commit()
print("Utilisateur cree avec succes")
db.close()
