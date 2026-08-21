import pytest
import pytest_asyncio
from app.core.database import engine
from app.models.entities import Base

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
