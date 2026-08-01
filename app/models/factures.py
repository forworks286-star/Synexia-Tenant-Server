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
    ppa = Column(Float, nullable=True)  
    numero_facture = Column(String, nullable=True, unique=True)
    taux_tva = Column(Float, default=19.0)
    fournisseur_nif = Column(String, nullable=True)
    fournisseur_nis = Column(String, nullable=True)
    fournisseur_rc = Column(String, nullable=True)

    statut = Column(String, default="pending") 
    type_facture = Column(String, default="achat")  
    type_stock = Column(String, nullable=True)  
    image_url = Column(String, nullable=True)
    cree_manuellement = Column(Boolean, default=False)
    motif_creation_manuelle = Column(String, nullable=True)  
    motif_rejet = Column(String, nullable=True)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)  
    a_ete_modifiee = Column(Boolean, default=False)

    
    ocr_raw_json = Column(JSON, default=dict)
    incoherence_detectee = Column(Boolean, default=False)  

    bon_commande_id = Column(Integer, ForeignKey("bons_commande.id"), nullable=True)
    ecarts_bc = Column(JSON, nullable=True)
    ecart_compte_rendu = Column(String, nullable=True)
    statut_apres_ecart = Column(String, nullable=True)
