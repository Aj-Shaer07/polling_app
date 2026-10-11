from app.models.session import SessionStatus
from app.services.roster import initialize_roster


def setup_activated_student(client, db_session, student_id="241AI001"):
    initialize_roster(db_session, force_reset=True)
    resp = client.post("/api/auth/student-activate", json={
        "student_id": student_id,
        "new_password": "studentpassword123",
    })
    return resp.json()["access_token"]


def test_response_lifecycle_and_integrity(client, seeded_db):
    # 1. Log in as professor
    prof_login = client.post("/api/auth/login", json={"username": "prof_turing", "password": "profpassword123"})
    prof_token = prof_login.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    # 2. Professor creates session
    sess_resp = client.post("/api/sessions", json={"title": "Auction Theory & Strategy"}, headers=prof_headers)
    assert sess_resp.status_code == 200
    session_id = sess_resp.json()["id"]
    join_code = sess_resp.json()["join_code"]

    # 3. Professor creates question
    q_resp = client.post(f"/api/sessions/{session_id}/questions", json={
        "question_text": "In a second-price sealed-bid auction, should you bid above, below, or equal to your true valuation?",
        "question_type": "FACTUAL",
        "reference_answer": "Equal to true valuation",
        "choices": ["Above true valuation", "Equal to true valuation", "Below true valuation"],
        "confidence_required": True,
        "reasoning_required": True,
    }, headers=prof_headers)
    assert q_resp.status_code == 200
    question_id = q_resp.json()["id"]

    # 4. Activate student and join session
    student_token = setup_activated_student(client, seeded_db, "241AI001")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    join_resp = client.post("/api/sessions/join", json={"join_code": join_code}, headers=student_headers)
    assert join_resp.status_code == 200

    # 5. Try submitting before Round 1 is open (Status is DRAFT) -> Should fail
    sub_fail = client.post(f"/api/questions/{question_id}/responses/round1", json={
        "answer": "Above true valuation",
        "confidence": 4,
        "explanation": "To make sure I win the auction.",
    }, headers=student_headers)
    assert sub_fail.status_code == 400

    # 6. Professor opens Round 1
    open_r1 = client.post(f"/api/sessions/{session_id}/status", json={"status": "OPEN_ROUND_1"}, headers=prof_headers)
    assert open_r1.status_code == 200

    # 7. Student submits Round 1 response -> Should succeed
    sub_r1 = client.post(f"/api/questions/{question_id}/responses/round1", json={
        "answer": "Above true valuation",
        "confidence": 4,
        "explanation": "To make sure I win the auction without paying more than the second price.",
    }, headers=student_headers)
    assert sub_r1.status_code == 200
    r1_data = sub_r1.json()
    assert r1_data["answer"] == "Above true valuation"
    assert r1_data["confidence"] == 4

    # 8. Student attempts duplicate submission for Round 1 -> Should fail (400)
    dup_sub = client.post(f"/api/questions/{question_id}/responses/round1", json={
        "answer": "Equal to true valuation",
        "confidence": 5,
        "explanation": "Changed my mind before close.",
    }, headers=student_headers)
    assert dup_sub.status_code == 400

    # 9. Verify participation isolation: Round 1 answered, but Round 2 is PENDING
    part_resp = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers)
    assert part_resp.status_code == 200
    part_data = part_resp.json()
    assert part_data["round_1_answered"] == 1
    assert part_data["round_2_answered"] == 0  # CRITICAL: Round 1 must NOT mark Round 2 answered!
    assert part_data["round_2_pending"] == 45

    # 10. Student checks my-responses
    my_resp = client.get(f"/api/questions/{question_id}/my-responses", headers=student_headers)
    assert my_resp.status_code == 200
    assert len(my_resp.json()) == 1

    # 11. Professor advances session to ANALYZING and triggers AI analysis
    client.post(f"/api/sessions/{session_id}/status", json={"status": "ANALYZING"}, headers=prof_headers)
    analysis_resp = client.post(f"/api/questions/{question_id}/analyze", headers=prof_headers)
    assert analysis_resp.status_code == 200
    challenge_id = analysis_resp.json()["challenge_id"]

    # 12. Professor reviews & approves the challenge
    appr_resp = client.post(f"/api/challenges/{challenge_id}/review", json={
        "status": "APPROVED",
        "edited_text": "Suppose you value the item at $100 and bid $150. If someone else bids $120, what do you pay?",
        "instructor_notes": "Focused counterexample on paying more than valuation.",
    }, headers=prof_headers)
    assert appr_resp.status_code == 200

    # 13. Professor opens Round 2
    open_r2 = client.post(f"/api/sessions/{session_id}/status", json={"status": "OPEN_ROUND_2"}, headers=prof_headers)
    assert open_r2.status_code == 200

    # 14. Student views challenge
    ch_view = client.get(f"/api/questions/{question_id}/challenge", headers=student_headers)
    assert ch_view.status_code == 200
    assert "Suppose you value the item at $100" in ch_view.json()["challenge_text"]

    # 15. Student submits Round 2 revision
    rev_resp = client.post(f"/api/questions/{question_id}/responses/round2", json={
        "answer": "Equal to true valuation",
        "confidence": 5,
        "changed_answer": True,
        "change_reason": "Realized bidding above could force me to buy at a loss.",
    }, headers=student_headers)
    assert rev_resp.status_code == 200

    # 16. Verify participation counts again
    part_resp2 = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers)
    assert part_resp2.json()["round_2_answered"] == 1
    assert part_resp2.json()["round_2_pending"] == 44

    # 17. Verify aggregate transition matrix
    results_resp = client.get(f"/api/questions/{question_id}/results", headers=prof_headers)
    assert results_resp.status_code == 200
    res_data = results_resp.json()
    assert res_data["round_1_total"] == 1
    assert res_data["round_2_total"] == 1
    assert len(res_data["belief_transitions"]) == 1
    trans = res_data["belief_transitions"][0]
    assert trans["from_answer"] == "Above true valuation"
    assert trans["to_answer"] == "Equal to true valuation"
    assert trans["count"] == 1
