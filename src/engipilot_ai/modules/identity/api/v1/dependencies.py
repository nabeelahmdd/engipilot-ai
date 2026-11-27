"""Bearer access-token validation for protected Identity routes."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from engipilot_ai.modules.identity.tokens import (
    AccessClaims,
    InvalidAccessToken,
    validate_access_token,
)

_bearer = HTTPBearer(auto_error=False)


def require_access_claims(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
) -> AccessClaims:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return validate_access_token(credentials.credentials)
    except InvalidAccessToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


AuthClaims = Annotated[AccessClaims, Depends(require_access_claims)]
