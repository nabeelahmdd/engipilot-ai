"""Database operations for identity and authentication."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.models.auth_session import AuthSession
from engipilot_ai.modules.identity.models.email_outbox import EmailOutbox
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.rate_bucket import AuthRateBucket
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
    async def get_user_by_id_for_update(
        session: AsyncSession,
        *,
        user_id: int,
    ) -> User | None:
        """Lock user while checking refresh eligibility."""
        statement = (
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

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
    async def get_auth_session_for_update(
        session: AsyncSession,
        *,
        session_id: int,
    ) -> AuthSession | None:
        """Lock a specific device session during credential rotation."""
        statement = (
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

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

    @staticmethod
    async def get_verification_user_for_update(
        session: AsyncSession,
        token_hash: str,
    ) -> User | None:
        """Lock the account associated with an email verification token."""
        statement = (
            select(User)
            .join(OneTimeToken, OneTimeToken.user_id == User.id)
            .where(
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.purpose == "verify_email",
            )
            .with_for_update(of=User)
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

    @staticmethod
    async def get_verification_token_for_update(
        session: AsyncSession,
        *,
        token_hash: str,
        user_id: int,
    ) -> OneTimeToken | None:
        """Lock and refresh the exact verification-token row."""
        statement = (
            select(OneTimeToken)
            .where(
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "verify_email",
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

    @staticmethod
    async def get_latest_email_verification_token(
        session: AsyncSession,
        *,
        user_id: int,
    ) -> OneTimeToken | None:
        """Find the most recently issued email verification token."""
        statement = (
            select(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "verify_email",
            )
            .order_by(
                OneTimeToken.created_at.desc(),
                OneTimeToken.id.desc(),
            )
            .limit(1)
        )
        return await session.scalar(statement)

    @staticmethod
    async def expire_active_email_verification_tokens(
        session: AsyncSession,
        *,
        user_id: int,
        now: datetime,
    ) -> None:
        """Invalidate unconsumed, active email verification tokens."""
        statement = (
            update(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "verify_email",
                OneTimeToken.consumed_at.is_(None),
                OneTimeToken.expires_at > now,
            )
            .values(expires_at=now)
        )
        await session.execute(statement)

    @staticmethod
    async def create_email_outbox(
        session: AsyncSession,
        *,
        user_id: int,
        recipient_email: str,
        template: str,
        encrypted_payload: bytes,
    ) -> EmailOutbox:
        """Queue an encrypted email inside the caller's transaction."""
        record = EmailOutbox(
            user_id=user_id,
            recipient_email=recipient_email,
            template=template,
            encrypted_payload=encrypted_payload,
            status="pending",
        )

        session.add(record)
        await session.flush()

        return record

    @staticmethod
    async def claim_next_email(
        session: AsyncSession,
        now: datetime,
    ) -> EmailOutbox | None:
        """Claim one due email without blocking other workers."""

        # Finalize messages abandoned after the last allowed attempt.
        await session.execute(
            update(EmailOutbox)
            .where(
                EmailOutbox.status == "processing",
                EmailOutbox.locked_until <= now,
                EmailOutbox.attempt_count >= 5,
            )
            .values(status="failed", locked_until=None)
        )

        statement = (
            select(EmailOutbox)
            .where(
                EmailOutbox.attempt_count < 5,
                or_(
                    and_(
                        EmailOutbox.status == "pending",
                        EmailOutbox.available_at <= now,
                    ),
                    and_(
                        EmailOutbox.status == "processing",
                        EmailOutbox.locked_until <= now,
                    ),
                ),
            )
            .order_by(
                EmailOutbox.available_at,
                EmailOutbox.id,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        record = await session.scalar(statement)

        if record is None:
            return None

        record.status = "processing"
        record.attempt_count += 1
        record.locked_until = now + timedelta(seconds=120)

        await session.flush()
        return record

    @staticmethod
    async def finish_email(
        session: AsyncSession,
        *,
        email_id: int,
        lease_until: datetime,
        attempt_count: int,
        success: bool,
    ) -> bool:
        """Acknowledge only the current lease owner."""

        now = datetime.now(lease_until.tzinfo)

        statement = update(EmailOutbox).where(
            EmailOutbox.id == email_id,
            EmailOutbox.status == "processing",
            EmailOutbox.locked_until == lease_until,
        )

        if success:
            statement = statement.values(
                status="sent",
                sent_at=now,
                locked_until=None,
            )
        elif attempt_count >= 5:
            statement = statement.values(
                status="failed",
                locked_until=None,
            )
        else:
            delay = min(60 * (2 ** (attempt_count - 1)), 3600)

            statement = statement.values(
                status="pending",
                available_at=now + timedelta(seconds=delay),
                locked_until=None,
            )

        result = await session.scalar(statement.returning(EmailOutbox.id))
        return result is not None

    @staticmethod
    async def count_recent_verification_tokens(
        session: AsyncSession,
        *,
        user_id: int,
        since: datetime,
    ) -> int:
        """Count verification tokens created during a time window."""
        statement = (
            select(func.count())
            .select_from(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "verify_email",
                OneTimeToken.created_at >= since,
            )
        )

        return int(await session.scalar(statement) or 0)

    @staticmethod
    async def cancel_pending_verification_emails(
        session: AsyncSession,
        *,
        user_id: int,
    ) -> None:
        """Prevent pending emails from sending obsolete tokens."""
        await session.execute(
            update(EmailOutbox)
            .where(
                EmailOutbox.user_id == user_id,
                EmailOutbox.template == "verify_email",
                EmailOutbox.status == "pending",
            )
            .values(status="failed")
        )

    @staticmethod
    async def get_latest_password_reset_token(
        session: AsyncSession,
        *,
        user_id: int,
    ) -> OneTimeToken | None:
        statement = (
            select(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "reset_password",
            )
            .order_by(OneTimeToken.created_at.desc(), OneTimeToken.id.desc())
            .limit(1)
        )
        return await session.scalar(statement)

    @staticmethod
    async def count_recent_password_reset_tokens(
        session: AsyncSession,
        *,
        user_id: int,
        since: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "reset_password",
                OneTimeToken.created_at >= since,
            )
        )
        return int(await session.scalar(statement) or 0)

    @staticmethod
    async def expire_active_password_reset_tokens(
        session: AsyncSession,
        *,
        user_id: int,
        now: datetime,
    ) -> None:
        statement = (
            update(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == "reset_password",
                OneTimeToken.consumed_at.is_(None),
                OneTimeToken.expires_at > now,
            )
            .values(expires_at=now)
        )
        await session.execute(statement)

    @staticmethod
    async def cancel_pending_password_reset_emails(
        session: AsyncSession,
        *,
        user_id: int,
    ) -> None:
        # The existing schema has no "cancelled" status.
        await session.execute(
            update(EmailOutbox)
            .where(
                EmailOutbox.user_id == user_id,
                EmailOutbox.template == "reset_password",
                EmailOutbox.status == "pending",
            )
            .values(status="failed")
        )

    @staticmethod
    async def get_password_reset_token(
        session: AsyncSession,
        *,
        token_hash: str,
    ) -> OneTimeToken | None:
        """Avoid Argon2 CPU work for unknown or stale recovery tokens."""
        return await session.scalar(
            select(OneTimeToken).where(
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.purpose == "reset_password",
            )
        )

    @staticmethod
    async def get_password_reset_user_for_update(
        session: AsyncSession,
        *,
        token_hash: str,
    ) -> User | None:
        statement = (
            select(User)
            .join(OneTimeToken, OneTimeToken.user_id == User.id)
            .where(
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.purpose == "reset_password",
            )
            .with_for_update(of=User)
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

    @staticmethod
    async def get_password_reset_token_for_update(
        session: AsyncSession,
        *,
        user_id: int,
        token_hash: str,
    ) -> OneTimeToken | None:
        statement = (
            select(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.purpose == "reset_password",
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await session.scalar(statement)

    @staticmethod
    async def revoke_all_user_sessions(
        session: AsyncSession,
        *,
        user_id: int,
        now: datetime,
    ) -> None:
        await session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    @staticmethod
    async def get_auth_session_user_id(
        session: AsyncSession,
        *,
        session_id: int,
    ) -> int | None:
        """Read owner before locking a session to prevent lock inversion."""
        return await session.scalar(
            select(AuthSession.user_id).where(AuthSession.id == session_id)
        )


    @staticmethod
    async def increment_auth_rate_bucket(
        session: AsyncSession,
        *,
        bucket_key: str,
        now: datetime,
        cutoff: datetime,
    ) -> tuple[int, datetime]:
        """Atomically increase a shared fixed-window counter via PostgreSQL."""
        initial = insert(AuthRateBucket).values(
            bucket_key=bucket_key,
            hits=1,
            window_started_at=now,
        )
        expired = AuthRateBucket.window_started_at <= cutoff
        statement = (
            initial.on_conflict_do_update(
                index_elements=[AuthRateBucket.bucket_key],
                set_={
                    "hits": case(
                        (expired, 1),
                        else_=AuthRateBucket.hits + 1,
                    ),
                    "window_started_at": case(
                        (expired, now),
                        else_=AuthRateBucket.window_started_at,
                    ),
                },
            )
            .returning(
                AuthRateBucket.hits,
                AuthRateBucket.window_started_at,
            )
        )
        row = (await session.execute(statement)).one()
        return int(row[0]), row[1]
