import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.entities import Base
import app.core.database as app_db

TEST_DB_DIR = "/root/.openclaw/workspace/preventive_med_monitor/data/test_tmp"
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_suite.db")
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

os.makedirs(TEST_DB_DIR, exist_ok=True)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

app_db.engine = test_engine
app_db.AsyncSessionLocal = TestSessionLocal

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()
