from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ..core.database import get_db
from ..core.security import verify_device_key
from ..core.ws_manager import ws_manager
from ..models.integrations import CameraEvent, EnergieLog, AutomationEvent, FaceEvent
from ..models.alertes import Alerte
from ..models.factures import Facture

router = APIRouter()


async def _creer_alerte(db: Session, type: str, niveau: str, message: str,
                         source: str, meta: dict):
    alerte = Alerte(
        type=type, niveau=niveau, message=message,
        source_module=source, metadata_json=meta,
        timestamp=datetime.utcnow(), lu=False,
    )
    db.add(alerte)
    db.commit()
    await ws_manager.broadcast({
        "id": alerte.id, "type": type, "niveau": niveau,
        "message": message, "source_module": source,
        "timestamp": str(alerte.timestamp),
    })


# ── Camera Event (équipe IA) ───────────────────────────────────

class CameraEventRequest(BaseModel):
    camera_id: str
    type: str
    zone: Optional[str] = None
    video_clip_url: Optional[str] = None
    personne_id: Optional[str] = None
    personne_nom: Optional[str] = None
    confiance: Optional[float] = None
    raw_data: Dict[str, Any] = {}


@router.post("/camera-event")
async def recevoir_camera_event(
    req: CameraEventRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    event = CameraEvent(
        camera_id=req.camera_id, type=req.type, zone=req.zone,
        video_clip_url=req.video_clip_url, personne_id=req.personne_id,
        personne_nom=req.personne_nom,
        confiance=str(req.confiance) if req.confiance is not None else None,
        raw_data=req.raw_data, timestamp=datetime.utcnow(),
    )
    db.add(event)
    db.commit()

    if req.type in ("intrusion", "vol_detecte", "comportement_suspect", "objet_verrouille"):
        await _creer_alerte(
            db, type="securite", niveau="danger",
            message=f"ALERTE SECURITE: {req.type} — Zone: {req.zone}",
            source="ia_vision",
            meta={"camera_id": req.camera_id, "zone": req.zone,
                  "video_clip_url": req.video_clip_url},
        )
    elif req.type == "anomalie":
        await _creer_alerte(
            db, type="securite", niveau="warning",
            message=f"Anomalie detectee — Camera {req.camera_id} Zone: {req.zone}",
            source="ia_vision",
            meta={"camera_id": req.camera_id, "zone": req.zone},
        )
    return {"status": "received", "id": event.id}


# ── Face ID / Access Control (équipe IA) ──────────────────────

class FaceIdRequest(BaseModel):
    personne_id: Optional[str] = None
    nom: Optional[str] = None
    reconnu: bool = False
    confiance: Optional[float] = None
    zone: Optional[str] = None
    methode: str = "face_id"
    autorise: bool = False
    raw_data: Dict[str, Any] = {}


@router.post("/face-id")
async def recevoir_face_id(
    req: FaceIdRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    event = FaceEvent(
        personne_id=req.personne_id, nom=req.nom,
        reconnu=req.reconnu,
        confiance=str(req.confiance) if req.confiance is not None else None,
        zone=req.zone, methode=req.methode, autorise=req.autorise,
        timestamp=datetime.utcnow(), raw_data=req.raw_data,
    )
    db.add(event)
    db.commit()

    if not req.reconnu or not req.autorise:
        await _creer_alerte(
            db, type="acces", niveau="danger",
            message=f"Acces refuse — Personne non reconnue — Zone: {req.zone}",
            source="ia_face_id",
            meta={"zone": req.zone, "reconnu": req.reconnu},
        )
    return {"status": "received", "id": event.id}


@router.get("/face-events")
def get_face_events(limit: int = 50, db: Session = Depends(get_db),
                    _=Depends(verify_device_key)):
    events = db.query(FaceEvent).order_by(FaceEvent.timestamp.desc()).limit(limit).all()
    return {"results": [
        {"id": e.id, "personne_id": e.personne_id, "nom": e.nom,
         "reconnu": e.reconnu, "zone": e.zone, "autorise": e.autorise,
         "timestamp": str(e.timestamp)}
        for e in events
    ]}


# ── Automation Event (équipe Automatique — payload complet) ──

class AutomationHeader(BaseModel):
    schema_version: Optional[str] = None
    project: Optional[str] = None
    department: Optional[str] = None
    module: str
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    controller_brand: Optional[str] = None
    controller_model: Optional[str] = None
    site_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    zone_id: Optional[str] = None
    line_id: Optional[str] = None
    timestamp: Optional[str] = None


class AutomationPayload(BaseModel):
    header: AutomationHeader
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    states: Dict[str, Any] = {}
    lighting: Dict[str, Any] = {}
    hvac: Dict[str, Any] = {}
    energy: Dict[str, Any] = {}
    iot: Dict[str, Any] = {}
    maintenance: Dict[str, Any] = {}
    diagnostic: Dict[str, Any] = {}
    alarms: Dict[str, Any] = {}
    events: Dict[str, Any] = {}


class AutomationEventRequest(BaseModel):
    automation: AutomationPayload


_ALARM_LABELS = {
    "fire_detected": "INCENDIE DETECTE",
    "gas_detected": "FUITE DE GAZ DETECTEE",
    "water_leak_detected": "FUITE D'EAU DETECTEE",
    "emergency_active": "URGENCE ACTIVE",
    "over_temperature": "SURCHAUFFE DETECTEE",
    "power_failure": "COUPURE SECTEUR",
    "communication_fault": "DEFAUT DE COMMUNICATION",
    "sensor_fault": "DEFAUT CAPTEUR",
    "lamp_fault": "DEFAUT LUMINAIRE",
}

_CRITICAL_ALARMS = {"fire_detected", "gas_detected", "water_leak_detected",
                    "emergency_active", "over_temperature"}


@router.post("/automation-event")
async def recevoir_automation_event(
    req: AutomationEventRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    """
    Endpoint unique pour tous les modules de l'équipe Automatique
    (SmartLighting, HVAC, FireSystem, AccessControl, Energy, Conveyor...).
    Le payload complet est stocké tel quel — flexible pour tout module futur.
    """
    data = req.automation
    header = data.header

    alarms = data.alarms or {}
    has_alarm = any(bool(v) for v in alarms.values())

    full_payload = data.model_dump()

    event = AutomationEvent(
        device_id=header.device_id,
        device_name=header.device_name,
        device_type=header.device_type,
        controller_brand=header.controller_brand,
        controller_model=header.controller_model,
        module=header.module,
        site_id=header.site_id,
        warehouse_id=header.warehouse_id,
        zone_id=header.zone_id,
        line_id=header.line_id,
        payload=full_payload,
        has_alarm=has_alarm,
        timestamp=datetime.utcnow(),
        received_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Diffusion temps réel de l'état complet via WebSocket
    await ws_manager.broadcast({
        "type": "automation_update",
        "module": header.module,
        "zone_id": header.zone_id,
        "device_id": header.device_id,
        "payload": full_payload,
        "has_alarm": has_alarm,
        "timestamp": str(event.timestamp),
    })

    # Création d'alertes automatiques pour chaque alarme active
    for key, value in alarms.items():
        if value:
            niveau = "danger" if key in _CRITICAL_ALARMS else "warning"
            label = _ALARM_LABELS.get(key, key)
            await _creer_alerte(
                db, type="automation", niveau=niveau,
                message=f"{label} — {header.module} — Zone: {header.zone_id or 'N/A'}",
                source="automatique",
                meta={"device_id": header.device_id, "module": header.module,
                      "zone_id": header.zone_id, "alarm_key": key},
            )

    return {"status": "received", "id": event.id, "has_alarm": has_alarm}


@router.get("/automation-events")
def get_automation_events(
    module: Optional[str] = None,
    zone_id: Optional[str] = None,
    has_alarm: Optional[bool] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(verify_device_key),
):
    query = db.query(AutomationEvent).order_by(AutomationEvent.timestamp.desc())
    if module:
        query = query.filter(AutomationEvent.module == module)
    if zone_id:
        query = query.filter(AutomationEvent.zone_id == zone_id)
    
    if has_alarm is not None:
        query = query.filter(AutomationEvent.has_alarm == has_alarm)
        
    events = query.limit(limit).all()
    return {"results": [
        {
            "id": e.id, "device_id": e.device_id, "module": e.module,
            "zone_id": e.zone_id, "has_alarm": e.has_alarm,
            "payload": e.payload, "timestamp": str(e.timestamp),
        } for e in events
    ]}


@router.get("/automation-events/latest")
def get_latest_automation_per_zone(db: Session = Depends(get_db),
                                    _=Depends(verify_device_key)):
    """Retourne le dernier état connu pour chaque zone/module — utilisé par le Logiciel pour l'écran IoT."""
    from sqlalchemy import func
    subq = (
        db.query(
            AutomationEvent.zone_id,
            AutomationEvent.module,
            func.max(AutomationEvent.id).label("max_id"),
        )
        .group_by(AutomationEvent.zone_id, AutomationEvent.module)
        .subquery()
    )
    events = (
        db.query(AutomationEvent)
        .join(subq, AutomationEvent.id == subq.c.max_id)
        .all()
    )
    return {"results": [
        {
            "device_id": e.device_id, "module": e.module, "zone_id": e.zone_id,
            "has_alarm": e.has_alarm, "payload": e.payload, "timestamp": str(e.timestamp),
        } for e in events
    ]}


# ── OCR Result (équipe IA — factures) ─────────────────────────

class OcrResultRequest(BaseModel):
    fournisseur_nom: str
    type_facture: str = "achat"  # achat | vente
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
        type_facture=req.type_facture,
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


# ── Energie Log simplifié (compatibilité) ─────────────────────

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