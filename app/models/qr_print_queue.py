from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class FileImpressionQr(Base):
    __tablename__ = "file_impression_qr"

    id = Column(Integer, primary_key=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    date_ajout = Column(DateTime, nullable=False)

    lot = relationship("Lot", foreign_keys=[lot_id])