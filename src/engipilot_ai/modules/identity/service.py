"""Identity-related business operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.models.user import User


class ActiveUserNotFound(Exception):
    """User does not exist or is inactive."""


class IdentityService:
    @staticmethod
    async def require_active_user(
        session: AsyncSession,
        user_id: int,
    ) -> User:
        user = await session.get(User, user_id)

        if user is None or not user.is_active:
            raise ActiveUserNotFound("Active user not found")

        return user
