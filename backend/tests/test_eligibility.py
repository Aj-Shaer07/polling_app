from app.services.roster import get_standard_eligible_student_ids, initialize_roster, is_student_eligible
from app.models.roster import EligibleStudent


def test_standard_eligible_roster_composition():
    ids = get_standard_eligible_student_ids()
    assert len(ids) == 45, f"Expected exactly 45 IDs, got {len(ids)}"
    assert len(set(ids)) == 45, "All IDs must be unique"

    # Specific ID boundary checks
    assert "241AI001" in ids
    assert "241AI044" in ids
    assert "231AI007" in ids

    # Prohibited / out-of-bounds IDs
    assert "241AI045" not in ids
    assert "241AI000" not in ids
    assert "231AI008" not in ids


def test_eligibility_and_activation_workflow(client, db_session):
    # Initialize roster
    roster = initialize_roster(db_session, force_reset=True)
    assert len(roster) == 45

    # Check eligibility helper
    assert is_student_eligible(db_session, "241AI001") is True
    assert is_student_eligible(db_session, "241AI044") is True
    assert is_student_eligible(db_session, "231AI007") is True
    assert is_student_eligible(db_session, "241AI045") is False
    assert is_student_eligible(db_session, "999FAKE99") is False

    # Ineligible student attempting to activate -> 403 Forbidden
    ineligible_resp = client.post("/api/auth/student-activate", json={
        "student_id": "241AI045",
        "new_password": "mypassword123",
    })
    assert ineligible_resp.status_code == 403

    # Password too short -> 400 Bad Request
    short_pw_resp = client.post("/api/auth/student-activate", json={
        "student_id": "241AI001",
        "new_password": "123",
    })
    assert short_pw_resp.status_code == 400

    # Eligible student setting password -> 200 OK
    activate_resp = client.post("/api/auth/student-activate", json={
        "student_id": "241AI001",
        "new_password": "mypassword123",
    })
    assert activate_resp.status_code == 200
    act_data = activate_resp.json()
    assert act_data["student_id"] == "241AI001"
    assert "access_token" in act_data

    # Attempting to activate again -> 400 Bad Request (already claimed)
    re_activate = client.post("/api/auth/student-activate", json={
        "student_id": "241AI001",
        "new_password": "anotherpassword",
    })
    assert re_activate.status_code == 400

    # Student can now log in using student-login
    login_resp = client.post("/api/auth/student-login", json={
        "student_id": "241AI001",
        "password": "mypassword123",
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_admin_reset_student_activation(client, seeded_db):
    # 1. Activate student 241AI002
    act_resp = client.post("/api/auth/student-activate", json={
        "student_id": "241AI002",
        "new_password": "mistakepassword123",
    })
    assert act_resp.status_code == 200

    # 2. Cannot activate again -> 400
    re_resp = client.post("/api/auth/student-activate", json={
        "student_id": "241AI002",
        "new_password": "anotherpassword",
    })
    assert re_resp.status_code == 400

    # 3. Log in as admin
    client.cookies.clear()
    admin_login = client.post("/api/auth/login", json={"username": "admin_test", "password": "adminpassword123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Admin resets activation for 241AI002
    reset_resp = client.post("/api/admin/roster/241AI002/reset-activation", headers=admin_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["is_activated"] is False

    # 5. Clear cookies and student can now activate again cleanly
    client.cookies.clear()
    fresh_act = client.post("/api/auth/student-activate", json={
        "student_id": "241AI002",
        "new_password": "correctpassword123",
    })
    assert fresh_act.status_code == 200

    # 6. Student can log in with new password
    login_resp = client.post("/api/auth/student-login", json={
        "student_id": "241AI002",
        "password": "correctpassword123",
    })
    assert login_resp.status_code == 200
