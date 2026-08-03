from datetime import datetime
from sqlalchemy.orm import Session

from ..models.qr_print_queue import FileImpressionQr


def ajouter_a_file_impression(db: Session, lot_id: int):
    db.add(FileImpressionQr(lot_id=lot_id, date_ajout=datetime.utcnow()))
    db.commit()


def retirer_de_file_impression(db: Session, lot_id: int):
    db.query(FileImpressionQr).filter(FileImpressionQr.lot_id == lot_id).delete()
    db.commit()