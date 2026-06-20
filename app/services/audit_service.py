from sqlalchemy.orm import Session
from datetime import datetime
from ..models.audit import AuditLog

def enregistrer_audit(db: Session, user_id: int, action: str, table_cible: str,
                       enregistrement_id: int = None, avant: dict = None,
                       apres: dict = None, source_device: str = None):
    log = AuditLog(
        user_id=user_id, action=action, table_cible=table_cible,
        enregistrement_id=enregistrement_id, valeur_avant=avant,
        valeur_apres=apres, timestamp=datetime.utcnow(),
        source_device=source_device,
    )
    db.add(log)
    db.commit()
