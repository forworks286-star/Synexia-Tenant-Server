def _interpreter_acces_controle(v: dict) -> dict:
    au = bool(v.get("STATE_AU_Active"))
    manuel = bool(v.get("STATE_Mode_Manu"))
    statut = v.get("PLC_System_Status")
    if au or statut == 4:
        return {"niveau": "critique", "libelle": "Confinement / Arrêt d'urgence actif — nécessite un déverrouillage manuel à distance", "resolu_auto": False}
    if statut == 3:
        return {"niveau": "alerte", "libelle": "Alarme talonnage / LAPI non reconnue", "resolu_auto": None}
    if manuel or statut == 2:
        return {"niveau": "manuel", "libelle": "Mode manuel actif — vérification vidéo recommandée", "resolu_auto": None}
    if statut == 0:
        return {"niveau": "normal", "libelle": "Zone à l'arrêt", "resolu_auto": None}
    return {"niveau": "normal", "libelle": "Fonctionnement automatique normal", "resolu_auto": None}


def _interpreter_quai_reception(v: dict) -> dict:
    au = bool(v.get("STATE_Z2_AU_Quai"))
    statut = v.get("PLC_Z2_Status_Code")
    if au:
        return {"niveau": "critique", "libelle": "Arrêt d'urgence quai actif", "resolu_auto": False}
    if statut == 3:
        return {"niveau": "alerte", "libelle": "Contrôle de conformité en cours — vérification requise", "resolu_auto": None}
    if statut in (1, 2):
        return {"niveau": "manuel", "libelle": "Réception en cours de traitement", "resolu_auto": None}
    if statut == 4:
        return {"niveau": "normal", "libelle": "Marchandise validée, prête pour QR", "resolu_auto": True}
    return {"niveau": "normal", "libelle": "Zone vide", "resolu_auto": None}


PROFILS = {
    "acces_controle": {"interpreter": _interpreter_acces_controle},
    "quai_reception": {"interpreter": _interpreter_quai_reception},
}

NIVEAU_PRIORITE = {"critique": 0, "alerte": 1, "manuel": 2, "normal": 3}


def interpreter_zone(profil: str, valeurs: dict) -> dict:
    p = PROFILS.get(profil)
    if not p:
        return {"niveau": "normal", "libelle": "Profil inconnu", "resolu_auto": None}
    return p["interpreter"](valeurs)