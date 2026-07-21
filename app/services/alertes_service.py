from datetime import datetime
from sqlalchemy.orm import Session

from ..models.alertes import Alerte
from ..core.ws_manager import ws_manager


async def creer_alerte(db: Session, type: str, niveau: str, message: str,
                        source: str, meta: dict | None = None,
                        destinataire_id: int | None = None) -> Alerte:
    alerte = Alerte(
        type=type, niveau=niveau, message=message,
        source_module=source, metadata_json=meta or {},
        timestamp=datetime.utcnow(), lu=False, destinataire_id=destinataire_id,
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)

    payload = {
        "type": "new_alert",
        "id": alerte.id,
        "level": alerte.niveau,
        "title": alerte.type,
        "alert_type": alerte.type,
        "message": alerte.message,
        "source_module": alerte.source_module,
        "metadata_json": alerte.metadata_json,
        "created_at": alerte.timestamp.isoformat() + "Z",
        "is_read": False,
    }
    if destinataire_id:
        await ws_manager.send_to_user(destinataire_id, payload)
    else:
        await ws_manager.broadcast(payload)
    return alerte