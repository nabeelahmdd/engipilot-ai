"""Database operations for identity and authentication."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.models.auth_session import AuthSession
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.refresh_credential import (
    RefreshCredential,
)
from engipilot_ai.modules.identity.models.user import User


class IdentityRepository:
    @staticmethod
    async def get_user_by_email(
        session: AsyncSession,
        email: str,
    ) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.strip().lower())
        return await session.scalar(statement)

    @staticmethod
    async def get_user_by_email_for_update(
        session: AsyncSession,
        email: str,
    ) -> User | None:
        """Lock current user row for security-sensitive changes."""
        statement = (
            select(User)
            .where(func.lower(User.email) == email.strip().lower())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

    @staticmethod
    async def get_user_by_uuid(
        session: AsyncSession,
        user_uuid: uuid.UUID,
    ) -> User | None:
        return await session.scalar(select(User).where(User.uuid == user_uuid))

    @staticmethod
    async def create_user(
        session: AsyncSession,
        *,
        email: str,
        password_hash: str,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def create_one_time_token(
        session: AsyncSession,
        *,
        user_id: int,
        purpose: str,
        token_hash: str,
        expires_at: datetime,
    ) -> OneTimeToken:
        record = OneTimeToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def get_auth_context(
        session: AsyncSession,
        *,
        user_uuid: uuid.UUID,
        session_uuid: uuid.UUID,
    ) -> tuple[User, AuthSession] | None:
        statement = (
            select(User, AuthSession)
            .join(
                AuthSession,
                AuthSession.user_id == User.id,
            )
            .where(
                User.uuid == user_uuid,
                AuthSession.uuid == session_uuid,
            )
        )
        result = await session.execute(statement)
        record = result.one_or_none()

        if record is None:
            return None

        return record[0], record[1]

    @staticmethod
    async def create_auth_session(
        session: AsyncSession,
        *,
        user_id: int,
        client_type: str,
        expires_at: datetime,
        csrf_hash: str | None = None,
    ) -> AuthSession:
        record = AuthSession(
            user_id=user_id,
            client_type=client_type,
            expires_at=expires_at,
            csrf_hash=csrf_hash,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def create_refresh_credential(
        session: AsyncSession,
        *,
        session_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshCredential:
        record = RefreshCredential(
            session_id=session_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def get_refresh_credential_for_update(
        session: AsyncSession,
        token_hash: str,
    ) -> RefreshCredential | None:
        statement = (
            select(RefreshCredential)
            .where(RefreshCredential.token_hash == token_hash)
            .with_for_update()
        )
        return await session.scalar(statement)
