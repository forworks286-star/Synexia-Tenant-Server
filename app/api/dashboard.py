from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.produits import Produit
from ..models.factures import Facture
from ..models.alertes import Alerte
from ..models.mouvements import Mouvement
import datetime

router = APIRouter()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    today = datetime.date.today()
    today_m = db.query(Mouvement).filter(Mouvement.timestamp >= datetime.datetime.combine(today, datetime.time.min)).all()
    return {
        "total_products": db.query(Produit).count(),
        "today_entries": sum(m.quantite for m in today_m if m.type == "entree"),
        "today_exits": sum(m.quantite for m in today_m if m.type == "sortie"),
        "active_alerts": db.query(Alerte).filter(Alerte.lu == False).count(),
        "pending_invoices": db.query(Facture).filter(Facture.statut == "pending").count(),
        "availability": 98.2,
    }