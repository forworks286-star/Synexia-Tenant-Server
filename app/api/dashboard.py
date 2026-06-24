from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import datetime

from ..core.database import get_db
from ..core.security import require_role
from ..models.produits import Produit
from ..models.factures import Facture
from ..models.alertes import Alerte
from ..models.mouvements import Mouvement
from ..models.integrations import EnergieLog

router = APIRouter()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db),
              current_user=Depends(require_role("admin", "manager"))):
    today = datetime.date.today()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    today_m = db.query(Mouvement).filter(Mouvement.timestamp >= today_start).all()
    total = db.query(Produit).count()
    actifs = db.query(Produit).filter(Produit.statut_produit == "actif").count()
    produits = db.query(Produit).all()
    valeur_totale = sum(
        sum(l.quantite_physique for l in p.lots) * (p.prix_moyen_pondere or 0.0)
        for p in produits
    )
    return {
        "total_products": total,
        "today_entries": sum(m.quantite for m in today_m if m.type == "entree"),
        "today_exits": sum(m.quantite for m in today_m if m.type == "sortie"),
        "active_alerts": db.query(Alerte).filter(Alerte.lu == False).count(),
        "pending_invoices": db.query(Facture).filter(Facture.statut == "pending").count(),
        "valeur_stock_total": round(valeur_totale, 2),
        "availability": round((actifs / total * 100), 1) if total > 0 else 0.0,
    }


@router.get("/movements-chart")
def get_movements_chart(days: int = 7, db: Session = Depends(get_db),
                         current_user=Depends(require_role("admin", "manager"))):
    today = datetime.date.today()
    results = []
    for i in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)
        mouvements = db.query(Mouvement).filter(
            Mouvement.timestamp >= day_start,
            Mouvement.timestamp <= day_end,
        ).all()
        results.append({
            "date": str(day),
            "entrees": sum(m.quantite for m in mouvements if m.type == "entree"),
            "sorties": sum(m.quantite for m in mouvements if m.type == "sortie"),
        })
    return {"results": results}


@router.get("/energie")
def get_energie(db: Session = Depends(get_db),
                current_user=Depends(require_role("admin", "manager"))):
    logs = db.query(EnergieLog).order_by(EnergieLog.timestamp.desc()).limit(100).all()
    return {"results": [
        {"zone": l.zone, "consommation_kwh": l.consommation_kwh,
         "mode": l.mode, "timestamp": str(l.timestamp)}
        for l in logs
    ]}
