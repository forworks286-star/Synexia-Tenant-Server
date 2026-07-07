from datetime import datetime
from sqlalchemy.orm import Session

from ..models.alertes import Alerte
from ..core.ws_manager import ws_manager


async def creer_alerte(db: Session, type: str, niveau: str, message: str,
                        source: str, meta: dict | None = None) -> Alerte:
    """Source unique de vérité pour toute création d'alerte dans le système.
    Persiste l'alerte en DB, puis diffuse en temps réel EXACTEMENT le même
    format que GET /api/v1/alertes, pour garantir la cohérence entre
    reload (REST) et real-time (WebSocket)."""
    alerte = Alerte(
        type=type, niveau=niveau, message=message,
        source_module=source, metadata_json=meta or {},
        timestamp=datetime.utcnow(), lu=False,
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)
    await ws_manager.broadcast({
        "type": "new_alert",
        "id": alerte.id,
        "level": alerte.niveau,
        "title": alerte.type,
        "message": alerte.message,
        "source_module": alerte.source_module,
        "metadata_json": alerte.metadata_json,
        "created_at": str(alerte.timestamp),
        "is_read": alerte.lu,
    })
    return alerte