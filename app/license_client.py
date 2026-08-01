import httpx
from .core.config import settings


async def verifier_licence_au_demarrage() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.LICENSE_SERVER_URL}/verify",
                json={"license_key": settings.LICENSE_KEY},
            )
        return response.json().get("valid", False)
    except httpx.RequestError:
        return True
