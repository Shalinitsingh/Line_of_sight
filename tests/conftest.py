"""
Shared test fixtures: reset tenant data before each test (the global-unique-email
constraint makes signups non-idempotent otherwise), and dispose async engine pools
after each test so asyncpg connections don't leak across event loops.
"""

import pytest
from sqlalchemy import text

from app.db import ProvisionerSession, app_engine, provisioner_engine


@pytest.fixture(autouse=True)
async def _reset_db():
    async with ProvisionerSession() as s:
        async with s.begin():
            await s.execute(text("TRUNCATE organizations CASCADE"))
            await s.execute(text("TRUNCATE verification_codes"))
    yield
    await app_engine.dispose()
    await provisioner_engine.dispose()
