import httpx
from .core.config import settings

def verifier_licence_au_demarrage() -> bool:
    """
    Appelée une fois au démarrage du serveur, puis toutes les 24 heures.
    Si la connexion au serveur de licence échoue (pas d'internet), autorise le fonctionnement (Grace period).
    """
    try:
        response = httpx.post(
            f"{settings.LICENSE_SERVER_URL}/verify",
            json={"license_key": settings.LICENSE_KEY},
            timeout=5.0,
        )
        data = response.json()
        return data.get("valid", False)
    except httpx.RequestError:
        return True  # Pas d'internet = ne pas bloquer le client, Grace period automatique
