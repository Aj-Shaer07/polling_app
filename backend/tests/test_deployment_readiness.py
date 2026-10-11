import pytest
from starlette.websockets import WebSocketDisconnect
from app.config import Settings
from app.models.user import User, UserRole
from app.services.auth import hash_password


def test_health_endpoint_checks_database(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["database"] == "connected"


def test_production_config_validation_and_postgres_url_normalization():
    # 1. postgres:// and postgresql:// normalize to postgresql+psycopg2://
    s = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgres://user:pass@ep-cool.aws.neon.tech/neondb?sslmode=require",
        SECRET_KEY="a-very-strong-production-secret-key-at-least-32-bytes",
        CORS_ORIGINS="https://belief-stress-test.vercel.app",
    )
    assert s.DATABASE_URL.startswith("postgresql+psycopg2://")
    assert s.CORS_ORIGINS == ["https://belief-stress-test.vercel.app"]
    s.validate_for_startup()

    # 2. SQLite in production must be blocked
    s_sqlite = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./local.db",
        SECRET_KEY="a-very-strong-production-secret-key-at-least-32-bytes",
        CORS_ORIGINS="https://belief-stress-test.vercel.app",
    )
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        s_sqlite.validate_for_startup()

    # 3. Weak or default dev secret in production must be blocked
    s_weak = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:pass@ep-cool.aws.neon.tech/neondb",
        SECRET_KEY="too-short-secret",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        s_weak.validate_for_startup()

    # 4. Wildcard CORS in production must be blocked
    s_cors = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:pass@ep-cool.aws.neon.tech/neondb",
        SECRET_KEY="a-very-strong-production-secret-key-at-least-32-bytes",
        CORS_ORIGINS="*",
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        s_cors.validate_for_startup()


def test_websocket_authentication_and_session_isolation(client, db_session):
    from app.services.roster import initialize_roster
    initialize_roster(db_session, force_reset=False)

    # Create two professors and a session for prof1
    prof1 = User(
        username="ws_prof1",
        email="ws_prof1@edu.com",
        hashed_password=hash_password("ProfPass123!"),
        role=UserRole.PROFESSOR,
        is_active=True,
    )
    prof2 = User(
        username="ws_prof2",
        email="ws_prof2@edu.com",
        hashed_password=hash_password("ProfPass123!"),
        role=UserRole.PROFESSOR,
        is_active=True,
    )
    db_session.add_all([prof1, prof2])
    db_session.commit()

    p1_token = client.post("/api/auth/login", json={"username": "ws_prof1", "password": "ProfPass123!"}).json()["access_token"]
    p2_token = client.post("/api/auth/login", json={"username": "ws_prof2", "password": "ProfPass123!"}).json()["access_token"]

    sess_res = client.post(
        "/api/sessions",
        json={"title": "WS Auth Test Session"},
        headers={"Authorization": f"Bearer {p1_token}"},
    )
    session_id = sess_res.json()["id"]
    join_code = sess_res.json()["join_code"]

    # Activate two students: 241AI010 joins session, 241AI011 does NOT join session
    s1_token = client.post(
        "/api/auth/student-activate",
        json={"student_id": "241AI010", "new_password": "StudentPass1!"},
    ).json()["access_token"]
    s2_token = client.post(
        "/api/auth/student-activate",
        json={"student_id": "241AI011", "new_password": "StudentPass2!"},
    ).json()["access_token"]

    client.post(
        "/api/sessions/join",
        json={"join_code": join_code},
        headers={"Authorization": f"Bearer {s1_token}"},
    )

    # Clear client cookies so we test pure token authentication
    client.cookies.clear()

    # 1. Unauthenticated WebSocket connection is rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/sessions/{session_id}"):
            pass

    # 2. Another professor who does not own the session is rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/sessions/{session_id}?token={p2_token}"):
            pass

    # 3. Student who has NOT joined this session is rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/sessions/{session_id}?token={s2_token}"):
            pass

    # 4. Owning professor can connect and ping/pong
    with client.websocket_connect(f"/ws/sessions/{session_id}?token={p1_token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"

    # 5. Joined student can connect and ping/pong
    with client.websocket_connect(f"/ws/sessions/{session_id}?token={s1_token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
