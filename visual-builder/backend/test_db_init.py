"""Test database initialization."""
import asyncio
from app.db import init_db


async def main():
    """Test database initialization."""
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())
