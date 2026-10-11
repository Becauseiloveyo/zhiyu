import hashlib
import hmac

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from zhiyu.core.config import settings
from zhiyu.core.identity import ServicePrincipal

bearer = HTTPBearer(auto_error=False)


def require_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> ServicePrincipal:
    if not settings.service_tokens:
        raise HTTPException(status_code=503, detail="business_api_not_configured")
    if credentials is None or credentials.scheme.lower() != "bearer" or len(credentials.credentials) < 32:
        raise HTTPException(
            status_code=401, detail="authentication_required", headers={"WWW-Authenticate": "Bearer"}
        )
    digest = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    for expected, principal in settings.service_tokens.items():
        if hmac.compare_digest(digest, expected):
            return principal
    raise HTTPException(status_code=401, detail="invalid_credentials", headers={"WWW-Authenticate": "Bearer"})
