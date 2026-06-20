from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from ..core.database import Base

class Produit(Base):
    __tablename__ = "produits"

    id = Column(Integer, primary_key=True)

    # Identification (Master Data)
    sku = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    categorie = Column(String, nullable=True)
    qr_code = Column(String, unique=True, nullable=False)
    code_barre = Column(String, nullable=True)
    unite_mesure = Column(String, default="piece")  # piece | kg | litre | metre

    # Statut
    statut_produit = Column(String, default="actif")  # actif | bloque | obsolete | en_test

    # Stock
    seuil_critique = Column(Integer, default=10)
    stock_securite = Column(Integer, default=0)
    quantite_min_commande = Column(Integer, default=1)
    quantite_max_stock = Column(Integer, nullable=True)
    delai_livraison_jours = Column(Integer, nullable=True)

    # Financier
    prix_achat = Column(Float, default=0.0)
    prix_moyen_pondere = Column(Float, default=0.0)
    prix_vente = Column(Float, default=0.0)
    taux_tva = Column(Float, default=19.0)
    devise = Column(String, default="DZD")

    # International
    pays_origine = Column(String, nullable=True)
    numero_serie = Column(String, nullable=True)

    # Fournisseurs
    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)
    fournisseur_secondaire_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)

    # Médias
    photo_url = Column(String, nullable=True)

    # Audit (qui a créé/modifié)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modifie_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_creation = Column(DateTime, nullable=True)
    date_derniere_modification = Column(DateTime, nullable=True)

    # Champs personnalisés selon type de magasin (flexibilité totale)
    champs_extra = Column(JSON, default=dict)

    lots = relationship("Lot", back_populates="produit")
    fournisseur = relationship("Fournisseur", foreign_keys=[fournisseur_id])


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    numero_lot = Column(String, nullable=True)

    quantite_physique = Column(Integer, default=0)
    quantite_reservee = Column(Integer, default=0)

    statut = Column(String, default="disponible")  # disponible | quarantaine | defaut | endommage

    date_fabrication = Column(Date, nullable=True)
    date_expiration = Column(Date, nullable=True)
    date_entree_stock = Column(DateTime, nullable=True)
    date_dernier_mouvement = Column(DateTime, nullable=True)

    emplacement = Column(String, nullable=True)
    entrepot_id = Column(Integer, nullable=True)  # pour multi-entrepôts futur
    temperature_requise = Column(String, nullable=True)

    @property
    def quantite_disponible(self):
        return self.quantite_physique - self.quantite_reservee

    produit = relationship("Produit", back_populates="lots")


class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    dernier_prix = Column(Float, nullable=True)
