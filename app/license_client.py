import httpx
from .core.config import settings

def verifier_licence_au_demarrage() -> bool:
    """
    يُستدعى مرة عند بدء تشغيل السيرفر، ثم كل 24 ساعة
    إن فشل الاتصال بسيرفر الترخيص (لا إنترنت)، يسمح بالعمل (Grace period)
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
        return True  # لا إنترنت = لا نوقف عمل الزبون، Grace period تلقائي
