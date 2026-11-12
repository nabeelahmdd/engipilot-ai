"""CI database connectivity smoke test, using the same engine as the API."""

import asyncio

from sqlalchemy import text

from engipilot_ai.core.database import get_engine


async def main() -> None:
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
