from app.models.session import SessionStatus
from app.services.roster import initialize_roster, get_standard_eligible_student_ids


def test_simulation_all_45_students_workflow(client, seeded_db):
    """
    Comprehensive simulation testing:
    - Exactly 45 eligible students (241AI001-241AI044 + 231AI007).
    - Account activation for all 45 with individual credentials.
    - Joining the live session.
    - Round 1 submissions and duplicate rejection.
    - Professor live participation dashboard verification.
    - AI reasoning categorization and challenge review.
    - Round 2 revisions and belief transition matrix calculation.
    - Follow-up assessment question.
    """
    # 1. Initialize roster for all 45 students
    initialize_roster(seeded_db, force_reset=True)
    all_eligible_ids = get_standard_eligible_student_ids()
    assert len(all_eligible_ids) == 45, "Must have exactly 45 eligible student IDs"

    # 2. Activate all 45 students and store tokens
    student_tokens = {}
    for s_id in all_eligible_ids:
        act_resp = client.post("/api/auth/student-activate", json={
            "student_id": s_id,
            "new_password": f"pass_{s_id}_secret",
        })
        assert act_resp.status_code == 200, f"Failed activating student {s_id}: {act_resp.text}"
        student_tokens[s_id] = act_resp.json()["access_token"]

    assert len(student_tokens) == 45

    # 3. Professor logs in and creates session
    prof_login = client.post("/api/auth/login", json={"username": "prof_turing", "password": "profpassword123"})
    prof_token = prof_login.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    sess_resp = client.post("/api/sessions", json={"title": "Economics & Auction Design"}, headers=prof_headers)
    session_id = sess_resp.json()["id"]
    join_code = sess_resp.json()["join_code"]

    # 4. Professor creates initial question
    q_resp = client.post(f"/api/sessions/{session_id}/questions", json={
        "question_text": "In a second-price auction, what is the weakly dominant strategy?",
        "question_type": "FACTUAL",
        "reference_answer": "Bid true value",
        "choices": ["Bid above true value", "Bid true value", "Bid below true value"],
        "confidence_required": True,
        "reasoning_required": True,
    }, headers=prof_headers)
    question_id = q_resp.json()["id"]

    # 5. All 45 students join the session
    for s_id, token in student_tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        j_resp = client.post("/api/sessions/join", json={"join_code": join_code}, headers=headers)
        assert j_resp.status_code == 200

    # Verify participation dashboard after joining
    part_dash = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers).json()
    assert part_dash["eligible_total"] == 45
    assert part_dash["joined_count"] == 45
    assert part_dash["round_1_answered"] == 0
    assert part_dash["round_1_pending"] == 45

    # 6. Professor opens Round 1
    client.post(f"/api/sessions/{session_id}/status", json={"status": "OPEN_ROUND_1"}, headers=prof_headers)

    # 7. All 45 students submit responses:
    # 25 students submit "Bid above true value" (misconception)
    # 20 students submit "Bid true value"
    for idx, (s_id, token) in enumerate(student_tokens.items()):
        headers = {"Authorization": f"Bearer {token}"}
        if idx < 25:
            ans = "Bid above true value"
            conf = 4
            exp = "I want to maximize my probability of winning since I only pay second price."
        else:
            ans = "Bid true value"
            conf = 4
            exp = "Bidding true value guarantees you never pay more than it is worth to you."

        sub_resp = client.post(f"/api/questions/{question_id}/responses/round1", json={
            "answer": ans,
            "confidence": conf,
            "explanation": exp,
        }, headers=headers)
        assert sub_resp.status_code == 200, f"Submission failed for {s_id}: {sub_resp.text}"

        # Test duplicate rejection on every 10th student
        if idx % 10 == 0:
            dup_resp = client.post(f"/api/questions/{question_id}/responses/round1", json={
                "answer": ans,
                "confidence": conf,
                "explanation": "Duplicate attempt",
            }, headers=headers)
            assert dup_resp.status_code == 400

    # 8. Verify participation status for Round 1
    part_dash_r1 = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers).json()
    assert part_dash_r1["joined_count"] == 45
    assert part_dash_r1["round_1_answered"] == 45
    assert part_dash_r1["round_1_pending"] == 0
    assert part_dash_r1["round_2_answered"] == 0
    assert part_dash_r1["round_2_pending"] == 45

    # 9. Close Round 1 and run AI analysis
    client.post(f"/api/sessions/{session_id}/status", json={"status": "ANALYZING"}, headers=prof_headers)
    analysis = client.post(f"/api/questions/{question_id}/analyze", headers=prof_headers).json()
    assert analysis["status"] == "success"
    challenge_id = analysis["challenge_id"]

    # 10. Professor reviews and approves challenge
    client.post(f"/api/challenges/{challenge_id}/review", json={
        "status": "APPROVED",
        "edited_text": "Suppose you value the item at $100 and bid $150. Another bidder bids $120. You win and must pay $120. Did you gain or lose utility?",
        "instructor_notes": "Emphasizing negative utility outcome of overbidding.",
    }, headers=prof_headers)

    # 11. Professor opens Round 2
    client.post(f"/api/sessions/{session_id}/status", json={"status": "OPEN_ROUND_2"}, headers=prof_headers)

    # 12. All 45 students submit Round 2 revisions:
    # 20 of the 25 switch from "Bid above" to "Bid true value"
    # 5 retain "Bid above"
    # 20 retain "Bid true value"
    for idx, (s_id, token) in enumerate(student_tokens.items()):
        headers = {"Authorization": f"Bearer {token}"}
        if idx < 20:
            rev_ans = "Bid true value"
            changed = True
            reason = "Realized I could end up paying more than my valuation ($120 > $100)."
        elif idx < 25:
            rev_ans = "Bid above true value"
            changed = False
            reason = "I still want to win at any price."
        else:
            rev_ans = "Bid true value"
            changed = False
            reason = "Still believe true value is dominant."

        rev_resp = client.post(f"/api/questions/{question_id}/responses/round2", json={
            "answer": rev_ans,
            "confidence": 5,
            "changed_answer": changed,
            "change_reason": reason,
        }, headers=headers)
        assert rev_resp.status_code == 200, f"Revision failed for {s_id}: {rev_resp.text}"

    # 13. Verify participation dashboard for Round 2
    part_dash_r2 = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers).json()
    assert part_dash_r2["round_2_answered"] == 45
    assert part_dash_r2["round_2_pending"] == 0

    # 14. Verify Belief Transition Matrix & Aggregate Results
    res_resp = client.get(f"/api/questions/{question_id}/results", headers=prof_headers)
    assert res_resp.status_code == 200
    results = res_resp.json()
    assert results["round_1_total"] == 45
    assert results["round_2_total"] == 45

    transitions = results["belief_transitions"]
    # Check that 20 students made the switch from "Bid above true value" -> "Bid true value"
    switched_transition = next((t for t in transitions if t["from_answer"] == "Bid above true value" and t["to_answer"] == "Bid true value"), None)
    assert switched_transition is not None
    assert switched_transition["count"] == 20

    # 15. Create follow-up question
    fu_q = client.post(f"/api/sessions/{session_id}/questions", json={
        "question_text": "In a third-price auction where highest bidder pays the third-highest bid, is truthful bidding still always dominant?",
        "question_type": "FACTUAL",
        "reference_answer": "No",
        "choices": ["Yes", "No"],
        "is_follow_up": True,
    }, headers=prof_headers).json()
    fu_question_id = fu_q["id"]

    # 16. Professor advances session to FOLLOW_UP
    client.post(f"/api/sessions/{session_id}/status", json={"status": "FOLLOW_UP"}, headers=prof_headers)

    # 17. Students respond to follow-up assessment
    for idx, (s_id, token) in enumerate(student_tokens.items()):
        headers = {"Authorization": f"Bearer {token}"}
        fu_sub = client.post(f"/api/questions/{fu_question_id}/responses/followup", json={
            "answer": "No",
            "confidence": 4,
            "explanation": "Because pay-off depends on lower order statistics, deviating may be profitable.",
        }, headers=headers)
        assert fu_sub.status_code == 200

    # 18. Verify follow-up participation
    final_dash = client.get(f"/api/sessions/{session_id}/participation", headers=prof_headers).json()
    assert final_dash["follow_up_answered"] == 45
    assert final_dash["follow_up_pending"] == 0

    # 19. Complete session
    comp_resp = client.post(f"/api/sessions/{session_id}/status", json={"status": "COMPLETED"}, headers=prof_headers)
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "COMPLETED"
