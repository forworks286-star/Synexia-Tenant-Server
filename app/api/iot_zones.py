from fastapi import APIRouter, Depends, HTTPException, Header
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import settings
from ..core.ws_manager import ws_manager
from ..models.iot_zone import IoTZoneState, IoTZoneEvenement
from ..services.iot_service import interpreter_zone, NIVEAU_PRIORITE
from ..services.alertes_service import notifier_admins

router = APIRouter()


def verify_device_key_iot(x_device_key: str = Header(...)):
    if x_device_key != settings.DEVICE_API_KEY:
        raise HTTPException(status_code=403, detail="error_invalid_device_key")


class IngestionZoneRequest(BaseModel):
    zone_id: str
    nom: Optional[str] = None
    profil: Optional[str] = None
    values: dict


def _zone_to_dict(z: IoTZoneState) -> dict:
    interpretation = interpreter_zone(z.profil, z.valeurs or {})
    return {
        "zone_id": z.zone_id, "nom": z.nom, "profil": z.profil,
        "valeurs": z.valeurs,
        "derniere_maj": z.derniere_maj.isoformat() + "Z" if z.derniere_maj else None,
        **interpretation,
    }


@router.post("/ingest")
async def ingerer_zone(req: IngestionZoneRequest, db: Session = Depends(get_db),
                        current_user=Depends(verify_device_key_iot)):
    zone = db.query(IoTZoneState).filter(IoTZoneState.zone_id == req.zone_id).first()
    ancienne_interpretation = interpreter_zone(zone.profil, zone.valeurs or {}) if zone else None

    if not zone:
        zone = IoTZoneState(
            zone_id=req.zone_id, nom=req.nom or req.zone_id,
            profil=req.profil or "generique", valeurs=req.values,
            derniere_maj=datetime.utcnow(),
        )
        db.add(zone)
    else:
        zone.valeurs = req.values
        zone.derniere_maj = datetime.utcnow()
        if req.nom:
            zone.nom = req.nom
        if req.profil:
            zone.profil = req.profil
    db.commit()
    db.refresh(zone)

    nouvelle_interpretation = interpreter_zone(zone.profil, zone.valeurs or {})

    if (not ancienne_interpretation) or (ancienne_interpretation["niveau"] != nouvelle_interpretation["niveau"]):
        db.add(IoTZoneEvenement(
            zone_id=zone.zone_id, niveau=nouvelle_interpretation["niveau"],
            libelle=nouvelle_interpretation["libelle"], valeurs=req.values,
            date_creation=datetime.utcnow(),
        ))
        db.commit()
        if nouvelle_interpretation["niveau"] in ("critique", "alerte"):
            await notifier_admins(
                db, type="iot", niveau="danger" if nouvelle_interpretation["niveau"] == "critique" else "warning",
                message=f"{zone.nom} — {nouvelle_interpretation['libelle']}",
                source="automation", meta={"zone_id": zone.zone_id},
            )

    await ws_manager.broadcast({"type": "iot_update", "zone": _zone_to_dict(zone)})
    return {"status": "ok"}


@router.get("")
def lister_zones(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    zones = db.query(IoTZoneState).all()
    resultats = [_zone_to_dict(z) for z in zones]
    resultats.sort(key=lambda z: NIVEAU_PRIORITE.get(z["niveau"], 9))
    return {"results": resultats}


@router.get("/{zone_id}")
def get_zone(zone_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    zone = db.query(IoTZoneState).filter(IoTZoneState.zone_id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="error_not_found")
    evenements = db.query(IoTZoneEvenement).filter(IoTZoneEvenement.zone_id == zone_id) \
        .order_by(IoTZoneEvenement.id.desc()).limit(20).all()
    result = _zone_to_dict(zone)
    result["evenements"] = [
        {"niveau": e.niveau, "libelle": e.libelle, "date": e.date_creation.isoformat() + "Z"}
        for e in evenements
    ]
    return result