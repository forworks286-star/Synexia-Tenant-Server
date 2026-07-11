from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base


class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    dernier_prix = Column(Float, nullable=True)
    delai_livraison_jours = Column(Integer, nullable=True)


class Produit(Base):
    __tablename__ = "produits"

    id = Column(Integer, primary_key=True)

    # Identification (Master Data)
    sku = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    categorie = Column(String, nullable=True)
    type_stock = Column(String, default="marchandise")  # matiere_premiere | produit_fini | marchandise | consommable
    qr_code = Column(String, unique=True, nullable=False)
    code_barre = Column(String, nullable=True)
    unite_mesure = Column(String, default="piece")
    numero_serie = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)

    # International / Conformité
    pays_origine = Column(String, nullable=True)
    statut_produit = Column(String, default="actif")  
    # Optimisation (KPIs)
    seuil_critique = Column(Integer, default=10)
    stock_securite = Column(Integer, default=0)
    quantite_min_commande = Column(Integer, default=1)
    quantite_max_stock = Column(Integer, nullable=True)

    # Financier
    prix_achat = Column(Float, default=0.0)
    prix_moyen_pondere = Column(Float, default=0.0)
    prix_vente = Column(Float, default=0.0)
    taux_tva = Column(Float, default=19.0)
    devise = Column(String, default="DZD")

    # Fournisseurs
    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)
    fournisseur_secondaire_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)

    # Audit
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modifie_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_creation = Column(DateTime, nullable=True)
    date_derniere_modification = Column(DateTime, nullable=True)

    champs_extra = Column(JSON, default=dict)

    lots = relationship("Lot", back_populates="produit", foreign_keys="Lot.produit_id")
    fournisseur = relationship("Fournisseur", foreign_keys=[fournisseur_id])
    fournisseur_secondaire = relationship("Fournisseur", foreign_keys=[fournisseur_secondaire_id])


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    numero_lot = Column(String, nullable=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=True)

    quantite_physique = Column(Integer, default=0)
    quantite_reservee = Column(Integer, default=0)

    statut = Column(String, default="disponible")  

    date_fabrication = Column(Date, nullable=True)
    date_expiration = Column(Date, nullable=True)
    date_entree_stock = Column(DateTime, nullable=True)
    date_dernier_mouvement = Column(DateTime, nullable=True)

    emplacement = Column(String, nullable=True)
    entrepot_id = Column(Integer, nullable=True)
    temperature_requise = Column(String, nullable=True)

    @property
    def quantite_disponible(self):
        return self.quantite_physique - self.quantite_reservee

    produit = relationship("Produit", back_populates="lots", foreign_keys=[produit_id])
