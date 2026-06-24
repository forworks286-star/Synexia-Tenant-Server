import httpx
from .core.config import settings


async def verifier_licence_au_demarrage() -> bool:
    """
    Called once at server startup.
    Returns False if license invalid — server refuses to start.
    Returns True if no internet — grace period, client not blocked.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.LICENSE_SERVER_URL}/verify",
                json={"license_key": settings.LICENSE_KEY},
            )
        return response.json().get("valid", False)
    except httpx.RequestError:
        return True
