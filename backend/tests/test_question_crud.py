import pytest
from app.services.roster import initialize_roster


def test_question_editing_in_draft_and_benchmark_reveal(client, seeded_db):
    # 1. Log in as professor
    prof_login = client.post("/api/auth/login", json={"username": "prof_turing", "password": "profpassword123"})
    prof_token = prof_login.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    # 2. Create session
    sess_resp = client.post("/api/sessions", json={"title": "Strategic Pricing Lecture"}, headers=prof_headers)
    assert sess_resp.status_code == 200
    session_id = sess_resp.json()["id"]

    # 3. Create question in DRAFT
    q_create = client.post(f"/api/sessions/{session_id}/questions", json={
        "question_text": "Draft Question Prompt",
        "question_type": "FACTUAL",
        "reference_answer": "Initial Reference",
        "choices": ["A", "B", "C"],
        "confidence_required": True,
        "reasoning_required": True,
    }, headers=prof_headers)
    assert q_create.status_code == 200
    q_data = q_create.json()
    assert q_data["status"] == "DRAFT"
    question_id = q_data["id"]

    # 4. Professor edits question while in DRAFT -> Should succeed
    q_edit = client.put(f"/api/questions/{question_id}", json={
        "question_text": "Updated Question Prompt After Review",
        "question_type": "PREDICTION",
        "reference_answer": "Expected value: $100",
        "accepted_reasoning": "Must adjust for winner curse",
        "choices": None,
        "prediction_enabled": True,
    }, headers=prof_headers)
    assert q_edit.status_code == 200
    edited = q_edit.json()
    assert edited["question_text"] == "Updated Question Prompt After Review"
    assert edited["question_type"] == "PREDICTION"
    assert edited["reference_answer"] == "Expected value: $100"
    assert edited["accepted_reasoning"] == "Must adjust for winner curse"
    assert edited["prediction_enabled"] is True

    # 5. Activate student and view question
    initialize_roster(seeded_db, force_reset=True)
    stu_act = client.post("/api/auth/student-activate", json={
        "student_id": "241AI003",
        "new_password": "pass123456",
    })
    stu_token = stu_act.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}

    # In DRAFT, student cannot see reference_answer or accepted_reasoning
    stu_view = client.get(f"/api/questions/{question_id}", headers=stu_headers)
    assert stu_view.status_code == 200
    assert stu_view.json()["reference_answer"] is None
    assert stu_view.json()["accepted_reasoning"] is None

    # 6. Professor opens Round 1
    client.post(f"/api/questions/{question_id}/status", json={"status": "OPEN_ROUND_1"}, headers=prof_headers)

    # 7. Attempting to edit question now that status is NOT DRAFT -> Should return 400 Bad Request
    q_edit_blocked = client.put(f"/api/questions/{question_id}", json={
        "question_text": "Should not be able to edit during live round",
    }, headers=prof_headers)
    assert q_edit_blocked.status_code == 400
    assert "DRAFT" in q_edit_blocked.json()["detail"]

    # 8. Complete question
    client.post(f"/api/questions/{question_id}/status", json={"status": "COMPLETED"}, headers=prof_headers)

    # 9. Now that question is COMPLETED, student CAN view the instructor benchmark
    stu_completed_view = client.get(f"/api/questions/{question_id}", headers=stu_headers)
    assert stu_completed_view.status_code == 200
    assert stu_completed_view.json()["reference_answer"] == "Expected value: $100"
    assert stu_completed_view.json()["accepted_reasoning"] == "Must adjust for winner curse"
