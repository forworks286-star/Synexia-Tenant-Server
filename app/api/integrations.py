from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..core.database import get_db
from ..models.integrations import CameraEvent, EnergieLog
from ..models.factures import Facture

router = APIRouter()

# ── من فريق IA/Vision - كاميرات الأمان ──
class CameraEventRequest(BaseModel):
    camera_id: str
    type: str
    zone: Optional[str] = None
    video_clip_url: Optional[str] = None
    raw_data: Dict[str, Any] = {}

@router.post("/camera-event")
def recevoir_camera_event(req: CameraEventRequest, db: Session = Depends(get_db)):
    """Endpoint جاهز - فريق IA يستدعيه عند أي حدث كاميرا"""
    event = CameraEvent(
        camera_id=req.camera_id, type=req.type, zone=req.zone,
        video_clip_url=req.video_clip_url, raw_data=req.raw_data,
        timestamp=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    return {"status": "received", "id": event.id}


# ── من فريق IA - نتائج OCR الفواتير ──
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
def recevoir_resultat_ocr(req: OcrResultRequest, db: Session = Depends(get_db)):
    """Endpoint جاهز - فريق IA يرسل نتيجة قراءة الفاتورة هنا، بأي صيغة JSON إضافية"""
    incoherence = abs((req.montant_ht + req.montant_tva) - req.montant_ttc) > 0.01

    facture = Facture(
        fournisseur_nom=req.fournisseur_nom, date=req.date,
        montant_ht=req.montant_ht, montant_tva=req.montant_tva, montant_ttc=req.montant_ttc,
        ppa=req.ppa, image_url=req.image_url, ocr_raw_json=req.raw_json,
        incoherence_detectee=incoherence, statut="pending",
    )
    db.add(facture)
    db.commit()
    return {"status": "received", "id": facture.id, "incoherence_detectee": incoherence}


# ── من فريق Automatique/IoT - بيانات الطاقة ──
class EnergieLogRequest(BaseModel):
    zone: str
    consommation_kwh: str
    mode: str = "normal"
    raw_data: Dict[str, Any] = {}

@router.post("/energie-log")
def recevoir_log_energie(req: EnergieLogRequest, db: Session = Depends(get_db)):
    """Endpoint جاهز - فريق IoT يرسل بيانات الطاقة هنا"""
    log = EnergieLog(
        zone=req.zone, consommation_kwh=req.consommation_kwh,
        mode=req.mode, raw_data=req.raw_data, timestamp=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    return {"status": "received"}
