from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..core.database import get_db
from ..core.security import verify_device_key
from ..core.ws_manager import ws_manager
from ..models.integrations import CameraEvent, EnergieLog
from ..models.alertes import Alerte
from ..models.factures import Facture

router = APIRouter()


async def _creer_alerte(db: Session, type: str, niveau: str, message: str,
                         source: str, meta: dict):
    """Direct internal helper — no HTTP loop."""
    alerte = Alerte(
        type=type, niveau=niveau, message=message,
        source_module=source, metadata_json=meta,
        timestamp=datetime.utcnow(), lu=False,
    )
    db.add(alerte)
    db.commit()
    await ws_manager.broadcast({
        "id": alerte.id, "type": type, "niveau": niveau,
        "message": message, "timestamp": str(alerte.timestamp),
    })


class CameraEventRequest(BaseModel):
    camera_id: str
    type: str
    zone: Optional[str] = None
    video_clip_url: Optional[str] = None
    raw_data: Dict[str, Any] = {}


@router.post("/camera-event")
async def recevoir_camera_event(
    req: CameraEventRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    event = CameraEvent(
        camera_id=req.camera_id, type=req.type, zone=req.zone,
        video_clip_url=req.video_clip_url, raw_data=req.raw_data,
        timestamp=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    if req.type in ("intrusion", "objet_verrouille"):
        await _creer_alerte(
            db, type="securite", niveau="danger",
            message=f"Camera event: {req.type} — Zone: {req.zone}",
            source="ia_vision",
            meta={"camera_id": req.camera_id, "video_clip_url": req.video_clip_url},
        )
    return {"status": "received", "id": event.id}


class OcrResultRequest(BaseModel):
    fournisseur_nom: str
    date: str
    montant_ht: float
    montant_tva: float
    montant_ttc: float
    ppa: Optional[float] = None
    image_url: Optional[str] = None
    raw_json: Dict[str, Any] = {}


@router.post("/ocr-result")
async def recevoir_resultat_ocr(
    req: OcrResultRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    incoherence = abs((req.montant_ht + req.montant_tva) - req.montant_ttc) > 0.01
    facture = Facture(
        fournisseur_nom=req.fournisseur_nom, date=req.date,
        montant_ht=req.montant_ht, montant_tva=req.montant_tva,
        montant_ttc=req.montant_ttc, ppa=req.ppa,
        image_url=req.image_url, ocr_raw_json=req.raw_json,
        incoherence_detectee=incoherence, statut="pending",
    )
    db.add(facture)
    db.commit()
    if incoherence:
        await _creer_alerte(
            db, type="facture", niveau="warning",
            message=f"Incoherence detectee — {req.fournisseur_nom}",
            source="ia_ocr",
            meta={"facture_id": facture.id},
        )
    return {"status": "received", "id": facture.id, "incoherence_detectee": incoherence}


class EnergieLogRequest(BaseModel):
    zone: str
    consommation_kwh: str
    mode: str = "normal"
    raw_data: Dict[str, Any] = {}


@router.post("/energie-log")
async def recevoir_log_energie(
    req: EnergieLogRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    log = EnergieLog(
        zone=req.zone, consommation_kwh=req.consommation_kwh,
        mode=req.mode, raw_data=req.raw_data, timestamp=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    return {"status": "received"}
