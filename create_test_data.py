from app.core.database import SessionLocal
from app.models.users import User
from app.models.audit import AuditLog
from app.models.produits import Produit, Lot, Fournisseur
from app.models.mouvements import Mouvement
from app.models.factures import Facture
from app.models.alertes import Alerte, CommandeAuto
from app.models.integrations import CameraEvent, EnergieLog, AutomationEvent, FaceEvent
from app.models.tenant_config import TenantConfig
from datetime import date, datetime

db = SessionLocal()

# ── TenantConfig ──────────────────────────────────────────────
existing = db.query(TenantConfig).first()
if not existing:
    config = TenantConfig(
        tenant_name="Entrepot Central Alger",
        tenant_type="supermarche",
        module_fefo=True,
        module_photo_obligatoire=False,
        module_camera_security=True,
        module_iot_energie=True,
        module_ocr_factures=True,
    )
    db.add(config)
else:
    existing.tenant_name = "Entrepot Central Alger"
    existing.tenant_type = "supermarche"
    existing.module_fefo = True
    existing.module_photo_obligatoire = False
    existing.module_camera_security = True
    existing.module_iot_energie = True
    existing.module_ocr_factures = True
db.commit()

# ── Fournisseurs ──────────────────────────────────────────────
f1 = Fournisseur(nom="TechNet DZ",   contact="0555000001", dernier_prix=800.0,  delai_livraison_jours=7)
f2 = Fournisseur(nom="NetPro Alger", contact="0556000002", dernier_prix=850.0,  delai_livraison_jours=5)
f3 = Fournisseur(nom="MediSupply",   contact="0557000003", dernier_prix=1200.0, delai_livraison_jours=3)
f4 = Fournisseur(nom="FoodDist DZ",  contact="0558000004", dernier_prix=450.0,  delai_livraison_jours=2)
for f in [f1, f2, f3, f4]:
    db.add(f)
db.commit()
for f in [f1, f2, f3, f4]:
    db.refresh(f)

# ── Produits ──────────────────────────────────────────────────
p1 = Produit(
    sku="SKU-RJ45-001", nom="Cable RJ45 Cat6", categorie="Reseau",
    qr_code="QR-RJ45-001", code_barre="6111234567890",
    unite_mesure="piece", numero_serie="SN-2026-001",
    pays_origine="Chine", statut_produit="actif",
    seuil_critique=20, stock_securite=10,
    quantite_min_commande=50, quantite_max_stock=500,
    prix_achat=800.0, prix_moyen_pondere=815.0, prix_vente=1200.0,
    taux_tva=19.0, devise="DZD",
    fournisseur_id=f1.id, fournisseur_secondaire_id=f2.id,
    date_creation=datetime.utcnow(),
)
p2 = Produit(
    sku="SKU-PARA-002", nom="Paracetamol 500mg", categorie="Pharmacie",
    qr_code="QR-PARA-002", code_barre="6111234567891",
    unite_mesure="boite", numero_serie=None,
    pays_origine="Algerie", statut_produit="actif",
    seuil_critique=50, stock_securite=20,
    quantite_min_commande=100, quantite_max_stock=1000,
    prix_achat=120.0, prix_moyen_pondere=125.0, prix_vente=180.0,
    taux_tva=9.0, devise="DZD",
    fournisseur_id=f3.id, fournisseur_secondaire_id=None,
    date_creation=datetime.utcnow(),
)
p3 = Produit(
    sku="SKU-LAIT-003", nom="Lait UHT 1L", categorie="Alimentaire",
    qr_code="QR-LAIT-003", code_barre="6111234567892",
    unite_mesure="carton", numero_serie=None,
    pays_origine="Algerie", statut_produit="actif",
    seuil_critique=30, stock_securite=15,
    quantite_min_commande=60, quantite_max_stock=600,
    prix_achat=45.0, prix_moyen_pondere=46.0, prix_vente=65.0,
    taux_tva=9.0, devise="DZD",
    fournisseur_id=f4.id, fournisseur_secondaire_id=None,
    date_creation=datetime.utcnow(),
)
p4 = Produit(
    sku="SKU-HDMI-004", nom="Cable HDMI 4K", categorie="Electronique",
    qr_code="QR-HDMI-004", code_barre="6111234567893",
    unite_mesure="piece", numero_serie="SN-2026-004",
    pays_origine="Chine", statut_produit="bloque",
    seuil_critique=10, stock_securite=5,
    quantite_min_commande=20, quantite_max_stock=200,
    prix_achat=350.0, prix_moyen_pondere=355.0, prix_vente=550.0,
    taux_tva=19.0, devise="DZD",
    fournisseur_id=f1.id, fournisseur_secondaire_id=f2.id,
    date_creation=datetime.utcnow(),
)
p5 = Produit(
    sku="SKU-SW24-005", nom="Switch 24 ports Cisco", categorie="Reseau",
    qr_code="QR-SW24-005", code_barre="6111234567894",
    unite_mesure="piece", numero_serie="SN-2026-005",
    pays_origine="USA", statut_produit="actif",
    seuil_critique=5, stock_securite=2,
    quantite_min_commande=10, quantite_max_stock=50,
    prix_achat=45000.0, prix_moyen_pondere=45500.0, prix_vente=65000.0,
    taux_tva=19.0, devise="DZD",
    fournisseur_id=f2.id, fournisseur_secondaire_id=None,
    date_creation=datetime.utcnow(),
)
p6 = Produit(
    sku="SKU-DOLIP-006", nom="Doliprane 1000mg", categorie="Pharmacie",
    qr_code="QR-DOLIP-006", code_barre="6111234567895",
    unite_mesure="boite", numero_serie=None,
    pays_origine="France", statut_produit="actif",
    seuil_critique=40, stock_securite=10,
    quantite_min_commande=80, quantite_max_stock=800,
    prix_achat=200.0, prix_moyen_pondere=205.0, prix_vente=280.0,
    taux_tva=9.0, devise="DZD",
    fournisseur_id=f3.id, fournisseur_secondaire_id=None,
    date_creation=datetime.utcnow(),
)
p7 = Produit(
    sku="SKU-HUILE-007", nom="Huile de Table 5L", categorie="Alimentaire",
    qr_code="QR-HUILE-007", code_barre="6111234567896",
    unite_mesure="bidon", numero_serie=None,
    pays_origine="Algerie", statut_produit="actif",
    seuil_critique=25, stock_securite=10,
    quantite_min_commande=50, quantite_max_stock=500,
    prix_achat=680.0, prix_moyen_pondere=690.0, prix_vente=850.0,
    taux_tva=9.0, devise="DZD",
    fournisseur_id=f4.id, fournisseur_secondaire_id=None,
    date_creation=datetime.utcnow(),
)
p8 = Produit(
    sku="SKU-ROUTER-008", nom="Routeur WiFi 6 TP-Link", categorie="Reseau",
    qr_code="QR-ROUTER-008", code_barre="6111234567897",
    unite_mesure="piece", numero_serie="SN-2026-008",
    pays_origine="Chine", statut_produit="actif",
    seuil_critique=8, stock_securite=3,
    quantite_min_commande=15, quantite_max_stock=100,
    prix_achat=12000.0, prix_moyen_pondere=12200.0, prix_vente=18000.0,
    taux_tva=19.0, devise="DZD",
    fournisseur_id=f1.id, fournisseur_secondaire_id=f2.id,
    date_creation=datetime.utcnow(),
)
for p in [p1, p2, p3, p4, p5, p6, p7, p8]:
    db.add(p)
db.commit()
for p in [p1, p2, p3, p4, p5, p6, p7, p8]:
    db.refresh(p)

# ── Lots ──────────────────────────────────────────────────────
l1a = Lot(produit_id=p1.id, numero_lot="LOT-RJ45-A",
    quantite_physique=142, quantite_reservee=12,
    statut="disponible", emplacement="Allee 3, Rack B",
    date_fabrication=date(2026, 1, 10), date_expiration=date(2028, 1, 10),
    date_entree_stock=datetime(2026, 1, 15))
l1b = Lot(produit_id=p1.id, numero_lot="LOT-RJ45-B",
    quantite_physique=80, quantite_reservee=0,
    statut="disponible", emplacement="Allee 3, Rack C",
    date_fabrication=date(2026, 3, 1), date_expiration=date(2028, 3, 1),
    date_entree_stock=datetime(2026, 3, 10))
l2a = Lot(produit_id=p2.id, numero_lot="LOT-PARA-A",
    quantite_physique=8, quantite_reservee=0,
    statut="disponible", emplacement="Allee 1, Rack A",
    date_fabrication=date(2025, 6, 1), date_expiration=date(2027, 6, 1),
    date_entree_stock=datetime(2025, 7, 1))
l3a = Lot(produit_id=p3.id, numero_lot="LOT-LAIT-A",
    quantite_physique=22, quantite_reservee=2,
    statut="disponible", emplacement="Allee 5, Rack A",
    date_fabrication=date(2026, 5, 1), date_expiration=date(2026, 8, 1),
    date_entree_stock=datetime(2026, 5, 15))
l4a = Lot(produit_id=p4.id, numero_lot="LOT-HDMI-A",
    quantite_physique=45, quantite_reservee=0,
    statut="quarantaine", emplacement="Allee 4, Rack D",
    date_fabrication=date(2026, 2, 1), date_expiration=date(2030, 2, 1),
    date_entree_stock=datetime(2026, 2, 20))
l5a = Lot(produit_id=p5.id, numero_lot="LOT-SW24-A",
    quantite_physique=12, quantite_reservee=0,
    statut="disponible", emplacement="Allee 2, Rack A",
    date_fabrication=date(2025, 11, 1), date_expiration=date(2030, 11, 1),
    date_entree_stock=datetime(2025, 12, 1))
l5b = Lot(produit_id=p5.id, numero_lot="LOT-SW24-B",
    quantite_physique=8, quantite_reservee=0,
    statut="disponible", emplacement="Allee 2, Rack B",
    date_fabrication=date(2026, 1, 15), date_expiration=date(2031, 1, 15),
    date_entree_stock=datetime(2026, 2, 1))
l6a = Lot(produit_id=p6.id, numero_lot="LOT-DOLIP-A",
    quantite_physique=35, quantite_reservee=0,
    statut="disponible", emplacement="Allee 1, Rack B",
    date_fabrication=date(2025, 8, 1), date_expiration=date(2026, 8, 15),
    date_entree_stock=datetime(2025, 9, 1))
l7a = Lot(produit_id=p7.id, numero_lot="LOT-HUILE-A",
    quantite_physique=180, quantite_reservee=0,
    statut="disponible", emplacement="Allee 6, Rack A",
    date_fabrication=date(2026, 4, 1), date_expiration=date(2027, 4, 1),
    date_entree_stock=datetime(2026, 4, 10))
l8a = Lot(produit_id=p8.id, numero_lot="LOT-ROUTER-A",
    quantite_physique=25, quantite_reservee=0,
    statut="disponible", emplacement="Allee 3, Rack A",
    date_fabrication=date(2026, 3, 1), date_expiration=date(2031, 3, 1),
    date_entree_stock=datetime(2026, 3, 15))
for l in [l1a, l1b, l2a, l3a, l4a, l5a, l5b, l6a, l7a, l8a]:
    db.add(l)
db.commit()
for l in [l1a, l1b, l2a, l3a, l4a, l5a, l5b, l6a, l7a, l8a]:
    db.refresh(l)

# ── Mouvements ────────────────────────────────────────────────
user = db.query(User).first()
uid = user.id if user else 1

mouvements = [
    Mouvement(produit_id=p1.id, lot_id=l1a.id, type="entree",  quantite=50,
        user_id=uid, timestamp=datetime(2026, 6, 20, 8, 0),
        synced=True, source_device="mobile", numero_bl="BL-2026-001"),
    Mouvement(produit_id=p1.id, lot_id=l1a.id, type="sortie",  quantite=20,
        user_id=uid, timestamp=datetime(2026, 6, 20, 10, 0),
        synced=True, source_device="mobile", numero_bl="BL-2026-002"),
    Mouvement(produit_id=p2.id, lot_id=l2a.id, type="entree",  quantite=100,
        user_id=uid, timestamp=datetime(2026, 6, 21, 9, 0),
        synced=True, source_device="desktop"),
    Mouvement(produit_id=p2.id, lot_id=l2a.id, type="sortie",  quantite=30,
        user_id=uid, timestamp=datetime(2026, 6, 21, 14, 0),
        synced=True, source_device="mobile"),
    Mouvement(produit_id=p3.id, lot_id=l3a.id, type="entree",  quantite=60,
        user_id=uid, timestamp=datetime(2026, 6, 22, 8, 30),
        synced=True, source_device="desktop", numero_bl="BL-2026-003"),
    Mouvement(produit_id=p3.id, lot_id=l3a.id, type="sortie",  quantite=15,
        user_id=uid, timestamp=datetime(2026, 6, 22, 16, 0),
        synced=True, source_device="mobile"),
    Mouvement(produit_id=p5.id, lot_id=l5a.id, type="entree",  quantite=12,
        user_id=uid, timestamp=datetime(2026, 6, 23, 9, 0),
        synced=True, source_device="desktop", numero_bl="BL-2026-004"),
    Mouvement(produit_id=p7.id, lot_id=l7a.id, type="entree",  quantite=200,
        user_id=uid, timestamp=datetime(2026, 6, 23, 11, 0),
        synced=True, source_device="desktop"),
    Mouvement(produit_id=p7.id, lot_id=l7a.id, type="sortie",  quantite=20,
        user_id=uid, timestamp=datetime(2026, 6, 24, 9, 0),
        synced=True, source_device="mobile"),
    Mouvement(produit_id=p8.id, lot_id=l8a.id, type="retour",  quantite=2,
        user_id=uid, timestamp=datetime(2026, 6, 24, 15, 0),
        synced=True, source_device="mobile"),
]
for m in mouvements:
    db.add(m)
db.commit()

# ── Factures ──────────────────────────────────────────────────
factures = [
    Facture(fournisseur_nom="TechNet DZ",   date=date(2026, 6, 20),
        montant_ht=84033.0, montant_tva=15966.27, montant_ttc=100000.0,
        statut="validated", incoherence_detectee=False, type_facture="achat",
        image_url="https://example.com/f1.jpg", ocr_raw_json={}),
    Facture(fournisseur_nom="MediSupply",   date=date(2026, 6, 21),
        montant_ht=55045.0, montant_tva=4954.0, montant_ttc=60000.0,
        statut="pending", incoherence_detectee=False, type_facture="achat",
        image_url="https://example.com/f2.jpg", ocr_raw_json={}),
    Facture(fournisseur_nom="FoodDist DZ",  date=date(2026, 6, 22),
        montant_ht=22935.0, montant_tva=2064.0, montant_ttc=25100.0,
        statut="pending", incoherence_detectee=True, type_facture="achat",
        image_url="https://example.com/f3.jpg", ocr_raw_json={}),
    Facture(fournisseur_nom="NetPro Alger", date=date(2026, 6, 23),
        montant_ht=180000.0, montant_tva=34200.0, montant_ttc=214200.0,
        statut="rejected", incoherence_detectee=False, type_facture="achat",
        image_url="https://example.com/f4.jpg", ocr_raw_json={}),
    Facture(fournisseur_nom="Client Boutique Centre", date=date(2026, 6, 25),
        montant_ht=126050.0, montant_tva=23949.5, montant_ttc=150000.0,
        statut="pending", incoherence_detectee=False, type_facture="vente",
        image_url="https://example.com/f5.jpg", ocr_raw_json={}),
]
for f in factures:
    db.add(f)
db.commit()

# ── Alertes ───────────────────────────────────────────────────
alertes = [
    Alerte(type="securite", niveau="danger",
        message="Intrusion detectee — Allee 3",
        source_module="ia_vision", metadata_json={"camera_id": "CAM-03"},
        timestamp=datetime(2026, 6, 24, 14, 30), lu=False),
    Alerte(type="stock", niveau="warning",
        message="Stock critique — Paracetamol 500mg (8 unites)",
        source_module="stock_monitor", metadata_json={"produit_id": p2.id},
        timestamp=datetime(2026, 6, 24, 10, 0), lu=False),
    Alerte(type="stock", niveau="warning",
        message="Stock bas — Lait UHT 1L (22 cartons)",
        source_module="stock_monitor", metadata_json={"produit_id": p3.id},
        timestamp=datetime(2026, 6, 24, 10, 1), lu=False),
    Alerte(type="facture", niveau="warning",
        message="Incoherence detectee — FoodDist DZ",
        source_module="ia_ocr", metadata_json={"facture_id": 3},
        timestamp=datetime(2026, 6, 22, 16, 0), lu=True),
    Alerte(type="energie", niveau="info",
        message="Mode eco active — Zone Allee 5",
        source_module="iot_gateway", metadata_json={"zone": "Allee 5"},
        timestamp=datetime(2026, 6, 24, 8, 0), lu=True),
    Alerte(type="securite", niveau="info",
        message="Objet verrouille deplace — Rack B",
        source_module="ia_vision", metadata_json={"camera_id": "CAM-02"},
        timestamp=datetime(2026, 6, 23, 17, 0), lu=True),
]
for a in alertes:
    db.add(a)
db.commit()

# ── Camera Events ─────────────────────────────────────────────
camera_events = [
    CameraEvent(camera_id="CAM-01", type="anomalie",
        zone="Allee 1", raw_data={"confidence": 0.92},
        timestamp=datetime(2026, 6, 24, 9, 0)),
    CameraEvent(camera_id="CAM-03", type="intrusion",
        zone="Allee 3", raw_data={"confidence": 0.98},
        timestamp=datetime(2026, 6, 24, 14, 30)),
    CameraEvent(camera_id="CAM-02", type="objet_verrouille",
        zone="Rack B", raw_data={"confidence": 0.87},
        timestamp=datetime(2026, 6, 23, 17, 0)),
]
for e in camera_events:
    db.add(e)
db.commit()

# ── Energie Logs ──────────────────────────────────────────────
energie_logs = [
    EnergieLog(zone="Allee 1", consommation_kwh="8.5",  mode="normal",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
    EnergieLog(zone="Allee 2", consommation_kwh="12.3", mode="normal",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
    EnergieLog(zone="Allee 3", consommation_kwh="6.1",  mode="eco",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
    EnergieLog(zone="Allee 4", consommation_kwh="0.8",  mode="eco",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
    EnergieLog(zone="Allee 5", consommation_kwh="4.2",  mode="eco",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
    EnergieLog(zone="Allee 6", consommation_kwh="9.7",  mode="normal",
        raw_data={}, timestamp=datetime(2026, 6, 24, 6, 0)),
]
for e in energie_logs:
    db.add(e)
db.commit()

# ── Automation Events (équipe Automatique) ─────────────────────
automation_events = [
    AutomationEvent(
        device_id="PLC_LIGHT_001", device_name="PLC Siemens S7-1200",
        device_type="PLC", controller_brand="Siemens", controller_model="S7-1200",
        module="SmartLighting", site_id="SITE_001", warehouse_id="WH_001",
        zone_id="ZONE_A01", line_id="LINE_01",
        payload={
            "header": {"module": "SmartLighting", "device_id": "PLC_LIGHT_001",
                       "zone_id": "ZONE_A01", "timestamp": "2026-06-28T08:30:15Z"},
            "inputs": {"presence": True, "motion": True, "lux": 185,
                       "temperature": 24.6, "humidity": 47.2, "co2": 650,
                       "smoke_detector": False, "emergency_button": False,
                       "auto_mode": True, "maintenance_mode": False},
            "outputs": {"light_level": 80, "relay_output": True, "alarm_output": False},
            "states": {"current_state": "OCCUPIED", "occupancy": True},
            "lighting": {"target_lux": 300, "measured_lux": 185, "dimming": 80, "eco_mode": False},
            "hvac": {},
            "energy": {"power_w": 420.6, "daily_energy_kwh": 8.45,
                       "monthly_energy_kwh": 241.8, "runtime_hours": 1254},
            "iot": {"mqtt_connected": True, "edge_gateway": "ONLINE"},
            "maintenance": {"maintenance_due": False, "remaining_hours": 523},
            "diagnostic": {"plc_status": "OK", "cpu_load": 34, "communication": "ONLINE"},
            "alarms": {"lamp_fault": False, "sensor_fault": False, "fire_detected": False,
                       "power_failure": False, "over_temperature": False},
            "events": {"last_event": "PresenceDetected", "event_counter": 25873},
        },
        has_alarm=False, timestamp=datetime(2026, 6, 28, 8, 30, 15),
        received_at=datetime.utcnow(),
    ),
    AutomationEvent(
        device_id="PLC_HVAC_002", device_name="PLC HVAC Zone B",
        device_type="PLC", controller_brand="Siemens", controller_model="S7-1200",
        module="HVAC", site_id="SITE_001", warehouse_id="WH_001",
        zone_id="ZONE_B01", line_id="LINE_02",
        payload={
            "header": {"module": "HVAC", "device_id": "PLC_HVAC_002", "zone_id": "ZONE_B01"},
            "inputs": {"temperature": 28.1, "humidity": 55.0, "co2": 800},
            "outputs": {"cooling_enable": True, "fan_speed": 70},
            "states": {"current_state": "COOLING"},
            "lighting": {},
            "hvac": {"target_temperature": 22, "actual_temperature": 28.1,
                      "target_humidity": 45, "actual_humidity": 55.0, "mode": "AUTO"},
            "energy": {"power_w": 850.0, "daily_energy_kwh": 15.2},
            "iot": {"mqtt_connected": True, "edge_gateway": "ONLINE"},
            "maintenance": {"maintenance_due": False},
            "diagnostic": {"plc_status": "OK", "hvac_status": "OK"},
            "alarms": {"over_temperature": True, "sensor_fault": False, "fire_detected": False},
            "events": {"last_event": "TemperatureHigh"},
        },
        has_alarm=True, timestamp=datetime(2026, 6, 28, 9, 0, 0),
        received_at=datetime.utcnow(),
    ),
    AutomationEvent(
        device_id="PLC_FIRE_003", device_name="PLC Fire System Zone C",
        device_type="PLC", controller_brand="Schneider", controller_model="M221",
        module="FireSystem", site_id="SITE_001", warehouse_id="WH_001",
        zone_id="ZONE_C01", line_id=None,
        payload={
            "header": {"module": "FireSystem", "device_id": "PLC_FIRE_003", "zone_id": "ZONE_C01"},
            "inputs": {"smoke_detector": False, "heat_detector": False, "gas_detector": False},
            "outputs": {"alarm_output": False, "emergency_shutdown": False},
            "states": {"current_state": "NORMAL"},
            "lighting": {}, "hvac": {}, "energy": {},
            "iot": {"mqtt_connected": True, "edge_gateway": "ONLINE"},
            "maintenance": {"last_service_date": "2026-05-01"},
            "diagnostic": {"plc_status": "OK"},
            "alarms": {"fire_detected": False, "gas_detected": False, "water_leak_detected": False},
            "events": {"last_event": "SystemCheck"},
        },
        has_alarm=False, timestamp=datetime(2026, 6, 28, 6, 0, 0),
        received_at=datetime.utcnow(),
    ),
]
for ae in automation_events:
    db.add(ae)
db.commit()

# ── Face Events (équipe IA — Access Control) ───────────────────
face_events = [
    FaceEvent(personne_id="EMP-001", nom="Ahmed Benali", reconnu=True,
        confiance="0.98", zone="Entree principale", methode="face_id",
        autorise=True, timestamp=datetime(2026, 6, 28, 8, 2, 0), raw_data={}),
    FaceEvent(personne_id="EMP-002", nom="Saadi Dadi", reconnu=True,
        confiance="0.99", zone="Zone Stock", methode="face_id",
        autorise=True, timestamp=datetime(2026, 6, 28, 8, 15, 0), raw_data={}),
    FaceEvent(personne_id=None, nom=None, reconnu=False,
        confiance="0.45", zone="Allee 3", methode="face_id",
        autorise=False, timestamp=datetime(2026, 6, 28, 13, 45, 0), raw_data={}),
]
for fe in face_events:
    db.add(fe)
db.commit()

# ── Automation — AccessControl (badge RFID + Face ID combiné) ─
ae_access = AutomationEvent(
    device_id="PLC_ACCESS_004", device_name="PLC Access Control Entree",
    device_type="PLC", controller_brand="Siemens", controller_model="S7-1200",
    module="AccessControl", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_ENTRY", line_id=None,
    payload={
        "header": {"module": "AccessControl", "device_id": "PLC_ACCESS_004", "zone_id": "ZONE_ENTRY"},
        "inputs": {"door_sensor": False, "manual_switch": False,
                   "emergency_button": False, "auto_mode": True,
                   "camera_presence": True, "power_available": True},
        "outputs": {"relay_output": True, "alarm_output": False,
                    "buzzer": False, "warning_light": False, "emergency_shutdown": False},
        "states": {"current_state": "ARMED", "automation_running": True,
                   "manual_override": False, "occupancy": False},
        "lighting": {}, "hvac": {},
        "energy": {"power_w": 45.0, "daily_energy_kwh": 0.8, "runtime_hours": 8760},
        "iot": {"mqtt_connected": True, "modbus_connected": True,
                "edge_gateway": "ONLINE", "network_latency_ms": 8},
        "maintenance": {"maintenance_due": False, "remaining_hours": 2190,
                        "last_service_date": "2026-04-01", "next_service_date": "2026-10-01"},
        "diagnostic": {"plc_status": "OK", "cpu_load": 12, "memory_usage": 28,
                       "scan_time_ms": 2.1, "communication": "ONLINE",
                       "sensor_status": "OK", "fault_code": 0, "fault_message": ""},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": False, "fire_detected": False,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": False},
        "events": {"last_event": "BadgeAccepted", "last_event_time": "2026-06-28T08:02:00Z",
                   "event_counter": 15432},
    },
    has_alarm=False, timestamp=datetime(2026, 6, 28, 8, 2, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_access)
db.commit()

# ── Automation — Energy Management (Smart Power) ───────────────
ae_energy = AutomationEvent(
    device_id="PLC_ENERGY_005", device_name="PLC Smart Power Management",
    device_type="PLC", controller_brand="Schneider", controller_model="TM221",
    module="Energy", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_GLOBAL", line_id=None,
    payload={
        "header": {"module": "Energy", "device_id": "PLC_ENERGY_005", "zone_id": "ZONE_GLOBAL"},
        "inputs": {"power_available": True, "energy_saving_mode": True,
                   "auto_mode": True, "manual_switch": False},
        "outputs": {"relay_output": True, "emergency_shutdown": False},
        "states": {"current_state": "ECO", "automation_running": True, "manual_override": False},
        "lighting": {}, "hvac": {},
        "energy": {
            "power_w": 12450.6, "current_a": 54.1, "voltage_v": 230,
            "frequency_hz": 50, "power_factor": 0.94,
            "daily_energy_kwh": 89.3, "monthly_energy_kwh": 2456.8,
            "yearly_energy_kwh": 28950.0, "runtime_hours": 8760,
            "energy_saving_percent": 28.4,
        },
        "iot": {"mqtt_connected": True, "modbus_connected": True,
                "edge_gateway": "ONLINE", "network_latency_ms": 5, "cloud_sync": True},
        "maintenance": {"maintenance_due": False, "predictive_maintenance": False,
                        "remaining_hours": 1460},
        "diagnostic": {"plc_status": "OK", "cpu_load": 22, "memory_usage": 41,
                       "scan_time_ms": 3.8, "communication": "ONLINE",
                       "fault_code": 0, "fault_message": ""},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": False, "fire_detected": False,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": False},
        "events": {"last_event": "EcoModeActivated", "last_event_time": "2026-06-28T06:00:00Z",
                   "event_counter": 8921},
    },
    has_alarm=False, timestamp=datetime(2026, 6, 28, 6, 0, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_energy)
db.commit()

# ── Automation — Fire System ALERTE ACTIVE (test alarm critique) ─
ae_fire_alarm = AutomationEvent(
    device_id="PLC_FIRE_006", device_name="PLC Fire System Zone D",
    device_type="PLC", controller_brand="Schneider", controller_model="M221",
    module="FireSystem", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_D01", line_id=None,
    payload={
        "header": {"module": "FireSystem", "device_id": "PLC_FIRE_006", "zone_id": "ZONE_D01"},
        "inputs": {"smoke_detector": True, "heat_detector": True,
                   "gas_detector": False, "water_leak": False,
                   "emergency_button": True, "auto_mode": True},
        "outputs": {"alarm_output": True, "buzzer": True, "warning_light": True,
                    "emergency_shutdown": True, "relay_output": False},
        "states": {"current_state": "FIRE_ALARM", "automation_running": True,
                   "manual_override": False, "occupancy": True},
        "lighting": {}, "hvac": {},
        "energy": {"power_w": 0, "daily_energy_kwh": 5.1},
        "iot": {"mqtt_connected": True, "edge_gateway": "ONLINE"},
        "maintenance": {"maintenance_due": False},
        "diagnostic": {"plc_status": "OK", "communication": "ONLINE",
                       "fault_code": 101, "fault_message": "FIRE DETECTED ZONE D"},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": True, "fire_detected": True,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": True},
        "events": {"last_event": "FireAlarm", "last_event_time": "2026-06-28T14:55:00Z",
                   "event_counter": 1},
    },
    has_alarm=True, timestamp=datetime(2026, 6, 28, 14, 55, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_fire_alarm)
db.commit()

# ── Automation — Warehouse AGV + Conveyor ──────────────────────
ae_warehouse = AutomationEvent(
    device_id="PLC_WH_007", device_name="PLC Warehouse Automation",
    device_type="PLC", controller_brand="Siemens", controller_model="S7-300",
    module="WarehouseAutomation", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_DOCK", line_id="LINE_03",
    payload={
        "header": {"module": "WarehouseAutomation", "device_id": "PLC_WH_007", "zone_id": "ZONE_DOCK"},
        "inputs": {"presence": True, "motion": True, "door_sensor": True,
                   "camera_presence": True, "auto_mode": True,
                   "emergency_button": False, "manual_switch": False},
        "outputs": {"relay_output": True, "light_level": 100,
                    "alarm_output": False, "emergency_shutdown": False},
        "states": {"current_state": "AGV_ACTIVE", "automation_running": True,
                   "manual_override": False, "occupancy": True},
        "lighting": {"dimming": 100, "eco_mode": False},
        "hvac": {},
        "energy": {"power_w": 2850.0, "daily_energy_kwh": 42.3, "runtime_hours": 3650},
        "iot": {"mqtt_connected": True, "modbus_connected": True,
                "edge_gateway": "ONLINE", "network_latency_ms": 6},
        "maintenance": {"maintenance_due": True, "predictive_maintenance": True,
                        "remaining_hours": 48, "next_service_date": "2026-07-03"},
        "diagnostic": {"plc_status": "OK", "cpu_load": 67, "memory_usage": 72,
                       "scan_time_ms": 8.5, "communication": "ONLINE",
                       "fault_code": 0, "fault_message": ""},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": False, "fire_detected": False,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": False},
        "events": {"last_event": "PaletteDetected", "last_event_time": "2026-06-28T11:30:00Z",
                   "event_counter": 4521},
    },
    has_alarm=False, timestamp=datetime(2026, 6, 28, 11, 30, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_warehouse)
db.commit()

# ── Automation — SmartLighting éteint (absence) ────────────────
ae_light_off = AutomationEvent(
    device_id="PLC_LIGHT_008", device_name="PLC Lighting Zone E",
    device_type="PLC", controller_brand="Siemens", controller_model="S7-1200",
    module="SmartLighting", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_E01", line_id="LINE_04",
    payload={
        "header": {"module": "SmartLighting", "device_id": "PLC_LIGHT_008", "zone_id": "ZONE_E01"},
        "inputs": {"presence": False, "motion": False, "lux": 420,
                   "temperature": 22.1, "humidity": 43.0, "co2": 580,
                   "smoke_detector": False, "emergency_button": False,
                   "auto_mode": True, "energy_saving_mode": True},
        "outputs": {"light_level": 0, "relay_output": False, "alarm_output": False},
        "states": {"current_state": "IDLE", "occupancy": False},
        "lighting": {"target_lux": 300, "measured_lux": 420, "dimming": 0,
                     "eco_mode": True, "occupancy_timeout_sec": 180},
        "hvac": {},
        "energy": {"power_w": 0, "daily_energy_kwh": 2.1,
                   "energy_saving_percent": 100.0, "runtime_hours": 890},
        "iot": {"mqtt_connected": True, "edge_gateway": "ONLINE", "network_latency_ms": 11},
        "maintenance": {"maintenance_due": False, "remaining_hours": 1100,
                        "lamp_status": "OK"},
        "diagnostic": {"plc_status": "OK", "cpu_load": 8, "lamp_status": "OK",
                       "communication": "ONLINE", "fault_code": 0, "fault_message": ""},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": False, "fire_detected": False,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": False},
        "events": {"last_event": "AbsenceTimeout", "last_event_time": "2026-06-28T10:15:00Z",
                   "event_counter": 12043},
    },
    has_alarm=False, timestamp=datetime(2026, 6, 28, 10, 15, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_light_off)
db.commit()

# ── Automation — HVAC maintenance requise ─────────────────────
ae_hvac_maint = AutomationEvent(
    device_id="PLC_HVAC_009", device_name="PLC HVAC Zone F",
    device_type="PLC", controller_brand="Siemens", controller_model="S7-1200",
    module="HVAC", site_id="SITE_001", warehouse_id="WH_001",
    zone_id="ZONE_F01", line_id="LINE_05",
    payload={
        "header": {"module": "HVAC", "device_id": "PLC_HVAC_009", "zone_id": "ZONE_F01"},
        "inputs": {"temperature": 21.8, "humidity": 44.5, "co2": 620,
                   "air_quality": 88, "auto_mode": True, "maintenance_mode": False},
        "outputs": {"hvac_enable": True, "cooling_enable": False,
                    "heating_enable": False, "fan_speed": 30, "damper_position": 25},
        "states": {"current_state": "NORMAL", "automation_running": True},
        "lighting": {},
        "hvac": {"mode": "AUTO", "target_temperature": 22, "actual_temperature": 21.8,
                  "target_humidity": 45, "actual_humidity": 44.5,
                  "target_co2": 800, "actual_co2": 620, "pid_output": 8.2},
        "energy": {"power_w": 380.0, "daily_energy_kwh": 6.8,
                   "monthly_energy_kwh": 198.4, "energy_saving_percent": 15.2},
        "iot": {"mqtt_connected": True, "modbus_connected": True,
                "edge_gateway": "ONLINE", "network_latency_ms": 9},
        "maintenance": {"maintenance_due": True, "predictive_maintenance": True,
                        "remaining_hours": 24, "last_service_date": "2026-01-15",
                        "next_service_date": "2026-07-02"},
        "diagnostic": {"plc_status": "OK", "cpu_load": 31, "hvac_status": "MAINTENANCE_REQUIRED",
                       "communication": "ONLINE", "fault_code": 5,
                       "fault_message": "Filter replacement required"},
        "alarms": {"lamp_fault": False, "sensor_fault": False,
                   "communication_fault": False, "power_failure": False,
                   "over_temperature": False, "fire_detected": False,
                   "gas_detected": False, "water_leak_detected": False,
                   "emergency_active": False},
        "events": {"last_event": "MaintenanceDue", "last_event_time": "2026-06-28T07:00:00Z",
                   "event_counter": 33201},
    },
    has_alarm=False, timestamp=datetime(2026, 6, 28, 7, 0, 0),
    received_at=datetime.utcnow(),
)
db.add(ae_hvac_maint)
db.commit()

# ── Face Events supplémentaires ────────────────────────────────
face_events_extra = [
    FaceEvent(personne_id="EMP-003", nom="Mohamed Larbi", reconnu=True,
        confiance="0.97", zone="Zone Stock", methode="badge",
        autorise=True, timestamp=datetime(2026, 6, 28, 9, 0, 0), raw_data={}),
    FaceEvent(personne_id="EMP-004", nom="Fatima Zohra", reconnu=True,
        confiance="0.96", zone="Entree principale", methode="face_id",
        autorise=True, timestamp=datetime(2026, 6, 28, 9, 30, 0), raw_data={}),
    FaceEvent(personne_id=None, nom=None, reconnu=False,
        confiance="0.31", zone="Zone D — Dock", methode="face_id",
        autorise=False, timestamp=datetime(2026, 6, 28, 14, 58, 0), raw_data={}),
    FaceEvent(personne_id="EMP-001", nom="Ahmed Benali", reconnu=True,
        confiance="0.99", zone="Zone Stock", methode="face_id",
        autorise=True, timestamp=datetime(2026, 6, 28, 15, 10, 0), raw_data={}),
]
for fe in face_events_extra:
    db.add(fe)
db.commit()

# ── Camera Events supplémentaires ─────────────────────────────
camera_events_extra = [
    CameraEvent(camera_id="CAM-04", type="vol_detecte",
        zone="Zone D", personne_id="INCONNU-001", confiance="0.91",
        raw_data={"action": "object_taken"}, timestamp=datetime(2026, 6, 28, 14, 56, 0)),
    CameraEvent(camera_id="CAM-05", type="comportement_suspect",
        zone="Allee 2", confiance="0.78",
        raw_data={"action": "loitering"}, timestamp=datetime(2026, 6, 28, 11, 0, 0)),
    CameraEvent(camera_id="CAM-01", type="anomalie",
        zone="Allee 1", confiance="0.85",
        raw_data={"type": "carton_endommage"}, timestamp=datetime(2026, 6, 28, 9, 45, 0)),
]
for ce in camera_events_extra:
    db.add(ce)
db.commit()

# ── Alertes supplémentaires (automation + face_id) ────────────
alertes_extra = [
    Alerte(type="automation", niveau="danger",
        message="INCENDIE DETECTE — FireSystem — Zone: ZONE_D01",
        source_module="automatique",
        metadata_json={"device_id": "PLC_FIRE_006", "zone_id": "ZONE_D01", "alarm_key": "fire_detected"},
        timestamp=datetime(2026, 6, 28, 14, 55, 0), lu=False),
    Alerte(type="automation", niveau="danger",
        message="URGENCE ACTIVE — FireSystem — Zone: ZONE_D01",
        source_module="automatique",
        metadata_json={"device_id": "PLC_FIRE_006", "zone_id": "ZONE_D01", "alarm_key": "emergency_active"},
        timestamp=datetime(2026, 6, 28, 14, 55, 1), lu=False),
    Alerte(type="acces", niveau="danger",
        message="Acces refuse — Personne non reconnue — Zone: Zone D — Dock",
        source_module="ia_face_id",
        metadata_json={"zone": "Zone D — Dock", "reconnu": False},
        timestamp=datetime(2026, 6, 28, 14, 58, 0), lu=False),
    Alerte(type="securite", niveau="danger",
        message="ALERTE SECURITE: vol_detecte — Zone: Zone D",
        source_module="ia_vision",
        metadata_json={"camera_id": "CAM-04", "zone": "Zone D"},
        timestamp=datetime(2026, 6, 28, 14, 56, 0), lu=False),
    Alerte(type="automation", niveau="warning",
        message="Surchauffe detectee — HVAC — Zone: ZONE_B01",
        source_module="automatique",
        metadata_json={"device_id": "PLC_HVAC_002", "zone_id": "ZONE_B01", "alarm_key": "over_temperature"},
        timestamp=datetime(2026, 6, 28, 9, 0, 0), lu=False),
]
for a in alertes_extra:
    db.add(a)
db.commit()

print("Donnees de test completes — tous les modules couverts:")
print("  SmartLighting x2 (occupie + eteint)")
print("  HVAC x2 (alarme surchauffe + maintenance requise)")
print("  FireSystem x2 (normal + ALARME INCENDIE)")
print("  AccessControl x1")
print("  Energy x1 (global)")
print("  WarehouseAutomation x1 (AGV + maintenance)")
print("  FaceEvent x7 (5 autorises + 2 refuses)")
print("  CameraEvent x6 (intrusion + vol + comportement suspect + anomalie)")
print("  Alertes x11 (danger + warning + info)")
db.close()
