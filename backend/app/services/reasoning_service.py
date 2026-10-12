from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.session import ClassroomSession, SessionStatus
from app.models.question import Question
from app.models.response import StudentResponse
from app.models.challenge import ReasoningCategory, ChallengeProposal, ChallengeStatus
from app.services.text_analysis import cluster_explanations
from app.services.aggregation import compute_answer_distributions
from app.services.llm_provider import get_ai_provider
from app.services.audit import log_audit_event


def analyze_round_1_and_propose_challenge(
    db: Session,
    session_id: str,
    question_id: str,
    professor_id: str,
) -> Dict[str, Any]:
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    
    question = db.query(Question).filter(Question.id == question_id, Question.session_id == session_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    # Fetch all round 1 responses
    responses = (
        db.query(StudentResponse)
        .filter(StudentResponse.question_id == question_id, StudentResponse.round_number == 1)
        .all()
    )

    # Compute authoritative answer distributions
    distributions = compute_answer_distributions(responses, question.reference_answer)
    dist_data = [d.model_dump() for d in distributions]

    # Extract anonymized explanations
    explanations = [r.explanation.strip() for r in responses if r.explanation and r.explanation.strip()]
    
    # 1. Cluster explanations with scikit-learn
    clusters = cluster_explanations(explanations)

    # 2. Call AI provider for structured reasoning analysis
    ai_provider = get_ai_provider()
    anonymized_responses = [{"answer": r.answer, "explanation": r.explanation, "confidence": r.confidence} for r in responses]
    
    ai_analysis = ai_provider.analyze_responses(
        question_text=question.question_text,
        question_type=question.question_type.value,
        reference_answer=question.reference_answer,
        responses_data=anonymized_responses,
        clusters=clusters,
        accepted_reasoning=question.accepted_reasoning,
    )

    # 3. Store reasoning categories in DB with authoritative counts and map student responses
    # Clear category_id on existing responses before deleting previous categories
    for r in responses:
        r.category_id = None
    db.flush()
    db.query(ReasoningCategory).filter(ReasoningCategory.question_id == question_id).delete()

    created_categories: List[ReasoningCategory] = []
    total_responses = len(responses)

    raw_cats = ai_analysis.get("categories", [])
    if not raw_cats:
        raw_cats = [{
            "title": "General Student Reasoning",
            "description": "General justifications submitted by respondents.",
            "is_misconception": False,
            "sample_explanations": explanations[:3],
            "response_indices": list(range(total_responses)),
        }]

    cat_count = len(raw_cats)
    assigned_indices = set()
    cat_index_map: Dict[int, List[int]] = {}

    for idx, c in enumerate(raw_cats):
        raw_indices = c.get("response_indices")
        if isinstance(raw_indices, list):
            valid_indices = [
                int(i) for i in raw_indices
                if isinstance(i, (int, float)) and 0 <= int(i) < total_responses and int(i) not in assigned_indices
            ]
            cat_index_map[idx] = valid_indices
            assigned_indices.update(valid_indices)
        else:
            cat_index_map[idx] = []

    # Distribute any unassigned response indices across categories
    unassigned = [i for i in range(total_responses) if i not in assigned_indices]
    for pos, resp_idx in enumerate(unassigned):
        target_cat = pos % cat_count if cat_count > 0 else 0
        cat_index_map.setdefault(target_cat, []).append(resp_idx)

    for idx, c in enumerate(raw_cats):
        mapped_indices = cat_index_map.get(idx, [])
        exact_count = len(mapped_indices)
        pct = round((exact_count / total_responses * 100), 1) if total_responses > 0 else 0.0

        sample_exps = c.get("sample_explanations") or [
            responses[i].explanation for i in mapped_indices if responses[i].explanation
        ][:3]

        cat_obj = ReasoningCategory(
            question_id=question_id,
            round_number=1,
            title=c.get("title", f"Category {idx + 1}"),
            description=c.get("description", "Identified reasoning pattern"),
            is_misconception=bool(c.get("is_misconception", False)),
            sample_explanations=sample_exps,
            response_count=exact_count,
            percentage=pct,
            is_ai_proposed=True,
            is_approved=False,
        )
        db.add(cat_obj)
        db.flush()
        for resp_idx in mapped_indices:
            responses[resp_idx].category_id = cat_obj.id
        created_categories.append(cat_obj)

    db.commit()

    # 4. Generate challenge proposal
    cats_for_challenge = [
        {
            "title": cat.title,
            "description": cat.description,
            "is_misconception": cat.is_misconception,
            "response_count": cat.response_count,
            "percentage": cat.percentage,
            "sample_explanations": cat.sample_explanations or [],
        }
        for cat in created_categories
    ]

    ch_data = ai_provider.generate_challenge(
        question_text=question.question_text,
        question_type=question.question_type.value,
        reference_answer=question.reference_answer,
        categories=cats_for_challenge,
        distributions=dist_data,
        accepted_reasoning=question.accepted_reasoning,
    )

    # Save challenge proposal
    db.query(ChallengeProposal).filter(ChallengeProposal.question_id == question_id).delete()
    
    challenge_obj = ChallengeProposal(
        question_id=question_id,
        challenge_type=ch_data.get("challenge_type", "COUNTEREXAMPLE"),
        challenge_text=ch_data.get("challenge_text", "Reflect on alternative edge scenarios."),
        targeted_reasoning_pattern=ch_data.get("targeted_reasoning_pattern", "General misconception"),
        relevance_evidence=ch_data.get("relevance_evidence", "Derived from Round 1 responses"),
        learning_objective=ch_data.get("learning_objective", "Deepen conceptual understanding"),
        assumptions_and_uncertainties=ch_data.get("assumptions_and_uncertainties", "Standard conditions"),
        status=ChallengeStatus.PROPOSED,
    )
    db.add(challenge_obj)

    # Update question & session status to CHALLENGE_PENDING
    question.status = "CHALLENGE_PENDING"
    session.status = SessionStatus.CHALLENGE_PENDING
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(challenge_obj)

    log_audit_event(
        db=db,
        action="ROUND_1_ANALYZED",
        resource_type="questions",
        resource_id=question_id,
        user_id=professor_id,
        details={"categories_count": len(created_categories), "challenge_id": challenge_obj.id},
    )

    return {
        "categories": created_categories,
        "challenge": challenge_obj,
        "distributions": distributions,
    }


def review_challenge_proposal(
    db: Session,
    challenge_id: str,
    status_choice: ChallengeStatus,
    edited_text: Optional[str],
    instructor_notes: Optional[str],
    professor_id: str,
) -> ChallengeProposal:
    challenge = db.query(ChallengeProposal).filter(ChallengeProposal.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge proposal not found.")

    challenge.status = status_choice
    if edited_text is not None:
        challenge.edited_text = edited_text.strip()
    if instructor_notes is not None:
        challenge.instructor_notes = instructor_notes.strip()
    
    challenge.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(challenge)

    log_audit_event(
        db=db,
        action="CHALLENGE_REVIEWED",
        resource_type="challenge_proposals",
        resource_id=challenge.id,
        user_id=professor_id,
        details={"status": status_choice.value},
    )

    return challenge
