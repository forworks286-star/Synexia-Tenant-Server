from sqlalchemy import Column, Integer, String, Float, Date, JSON, Boolean, ForeignKey
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
    numero_facture = Column(String, nullable=True, unique=True)
    taux_tva = Column(Float, default=19.0)
    fournisseur_nif = Column(String, nullable=True)
    fournisseur_nis = Column(String, nullable=True)
    fournisseur_rc = Column(String, nullable=True)

    statut = Column(String, default="pending")  # pending | validated | rejected
    type_facture = Column(String, default="achat")  # achat | vente | ajustement_manuel
    type_stock = Column(String, nullable=True)  # marchandise | matiere_premiere | produit_fini | consommable
    image_url = Column(String, nullable=True)
    cree_manuellement = Column(Boolean, default=False)
    motif_creation_manuelle = Column(String, nullable=True)  # compte-rendu obligatoire si cree_manuellement
    motif_rejet = Column(String, nullable=True)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # proprietaire de la facture (session)
    a_ete_modifiee = Column(Boolean, default=False)

    # JSON brut complet tel qu'envoyé par l'équipe IA - flexibilité totale pour tout changement de format futur
    ocr_raw_json = Column(JSON, default=dict)
    incoherence_detectee = Column(Boolean, default=False)  # alerte champ en rouge
