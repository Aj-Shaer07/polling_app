import os
import sys

# Ensure backend root is on sys.path and tests always use isolated in-memory SQLite
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GEMINI_API_KEY"] = ""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth import hash_password
from app.services.roster import initialize_roster

# In-memory SQLite for fast, isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db_session):
    # Initialize 45-student roster
    initialize_roster(db_session)

    # Seed Admin
    admin = User(
        username="admin_test",
        email="admin@test.edu",
        hashed_password=hash_password("adminpassword123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)

    # Seed Professor
    prof = User(
        username="prof_turing",
        email="turing@test.edu",
        hashed_password=hash_password("profpassword123"),
        role=UserRole.PROFESSOR,
        is_active=True,
    )
    db_session.add(prof)

    db_session.commit()
    return db_session
