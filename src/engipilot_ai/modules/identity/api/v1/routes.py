"""Identity API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.database import get_db_session
from engipilot_ai.modules.identity.api.v1.schemas.registration import (
    RegisterRequest,
    RegisterResponse,
)
from engipilot_ai.modules.identity.services import (
    EmailAlreadyRegistered,
    InvalidRegistrationData,
    RegistrationService,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer",
)
async def register(
    payload: RegisterRequest,
    session: DbSession,
) -> RegisterResponse:
    try:
        result = await RegistrationService.register(
            session,
            email=payload.email,
            password=payload.password.get_secret_value(),
            first_name=payload.first_name,
            last_name=payload.last_name,
        )

    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        ) from exc

    except InvalidRegistrationData as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        user_uuid=result.user_uuid,
        email_verification_required=True,
    )
