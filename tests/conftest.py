"""Pytest fixtures shared across the test suite."""
import os
import sys

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"
# Ensure the test database URL is available before importing application modules.
os.environ["DATABASE_URL"] = SQLALCHEMY_TEST_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

# Ensure the project root is importable when tests run from the tests directory.
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)

from database import Base, get_db
from main import app
import models

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_redis():
    """Patch all Redis cache calls so tests run without a Redis server."""
    with (
        patch("cache.get_cached_user", new_callable=AsyncMock, return_value=None),
        patch("cache.cache_user", new_callable=AsyncMock),
        patch("cache.invalidate_user_cache", new_callable=AsyncMock),
        patch("auth.get_cached_user", new_callable=AsyncMock, return_value=None),
        patch("auth.cache_user", new_callable=AsyncMock),
        patch("main.invalidate_user_cache", new_callable=AsyncMock),
    ):
        yield


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def test_user(db):
    """Create and return a regular test user."""
    import auth as auth_mod
    user = models.User(
        email="test@example.com",
        password=auth_mod.get_password_hash("password123"),
        is_verified=True,
        role=models.UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture()
def admin_user(db):
    """Create and return an admin test user."""
    import auth as auth_mod
    user = models.User(
        email="admin@example.com",
        password=auth_mod.get_password_hash("adminpass123"),
        is_verified=True,
        role=models.UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture()
def user_token(test_user):
    import auth as auth_mod
    return auth_mod.create_access_token(data={"sub": test_user.email})


@pytest.fixture()
def admin_token(admin_user):
    import auth as auth_mod
    return auth_mod.create_access_token(data={"sub": admin_user.email})
