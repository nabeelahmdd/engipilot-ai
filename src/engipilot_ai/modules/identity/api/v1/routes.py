"""Identity API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.database import get_db_session
from engipilot_ai.modules.identity.api.v1.schemas.login import (
    LoginRequest,
    LoginResponse,
)
from engipilot_ai.modules.identity.api.v1.schemas.registration import (
    RegisterRequest,
    RegisterResponse,
)
from engipilot_ai.modules.identity.api.v1.schemas.resend_verification import (
    ResendVerificationRequest,
    ResendVerificationResponse,
)
from engipilot_ai.modules.identity.api.v1.schemas.verification import (
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from engipilot_ai.modules.identity.services import (
    AccountDisabled,
    EmailAlreadyRegistered,
    EmailNotVerified,
    InvalidCredentials,
    LoginService,
    InvalidRegistrationData,
    RegistrationService,
)
from engipilot_ai.modules.identity.services.verification import (
    EmailVerificationService,
    InvalidVerificationToken,
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


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resend account verification email",
)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: DbSession,
) -> ResendVerificationResponse:
    await EmailVerificationService.resend_verification(
        session,
        email=str(payload.email),
    )

    return ResendVerificationResponse()


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify customer email address",
)
async def verify_email(
    payload: VerifyEmailRequest,
    session: DbSession,
) -> VerifyEmailResponse:
    try:
        user_uuid = await EmailVerificationService.verify_email(
            session,
            token=payload.token.get_secret_value(),
        )

    except InvalidVerificationToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        ) from exc

    return VerifyEmailResponse(
        user_uuid=user_uuid,
        email_verified=True,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Sign in with email and password",
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Email verification required"},
    },
)
async def login(
    payload: LoginRequest,
    response: Response,
    session: DbSession,
) -> LoginResponse:
    try:
        result = await LoginService.login(
            session,
            email=payload.email,
            password=payload.password.get_secret_value(),
            client_type="browser",
        )
    except (InvalidCredentials, AccountDisabled) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except EmailNotVerified as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        ) from exc

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    settings = get_settings()
    response.set_cookie(
        key="cp_refresh",
        value=result.refresh_token,
        max_age=settings.refresh_session_days * 86400,
        path="/api/v1/auth",
        httponly=True,
        secure=settings.app_env in ("staging", "production"),
        samesite="lax",
    )

    return LoginResponse(
        user_uuid=result.user_uuid,
        session_uuid=result.session_uuid,
        access_token=result.access_token,
        expires_in=result.expires_in,
        csrf_token=result.csrf_token,
    )
