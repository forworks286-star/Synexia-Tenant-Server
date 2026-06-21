from sqlalchemy import Column, Integer, String, Float, Date, JSON, Boolean
from ..core.database import Base

class Facture(Base):
    """
    Le champ ocr_raw_json reçoit n'importe quel format envoyé par l'équipe IA sans casser le code
    """
    __tablename__ = "factures"

    id = Column(Integer, primary_key=True)
    fournisseur_nom = Column(String, nullable=False)
    date = Column(Date, nullable=False)

    montant_ht = Column(Float, default=0.0)
    montant_tva = Column(Float, default=0.0)
    montant_ttc = Column(Float, default=0.0)
    ppa = Column(Float, nullable=True)  # Prix Public Algérien - pharmacies uniquement

    statut = Column(String, default="pending")  # pending | validated | rejected
    image_url = Column(String, nullable=True)

    # JSON brut complet tel qu'envoyé par l'équipe IA - flexibilité totale pour tout changement de format futur
    ocr_raw_json = Column(JSON, default=dict)
    incoherence_detectee = Column(Boolean, default=False)  # alerte champ en rouge
