from collections import defaultdict
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.question import Question, QuestionType
from app.models.response import StudentResponse
from app.schemas.response import (
    AnswerDistributionItem,
    ConfidenceDistributionItem,
    BeliefTransitionItem,
    AggregateAnalysisResponse,
)


import re


def _extract_option_parts(text: str) -> List[str]:
    """
    Given an answer or benchmark string like 'Option A: 6', 'A) 6', or '6',
    extract candidate normalized forms:
    - full string ('option a: 6')
    - option label ('option a', 'a')
    - option value after prefix ('6')
    """
    clean = text.strip().lower()
    if not clean:
        return []
    parts = [clean]
    m = re.match(r"^(?:(option\s+[a-z0-9]+)|([a-z0-9]))\s*[:\)\.\-\u2013\u2014]\s*(.+)$", clean)
    if m:
        label_full = (m.group(1) or m.group(2) or "").strip()
        value_part = (m.group(3) or "").strip()
        if label_full:
            parts.append(label_full)
            if label_full.startswith("option "):
                parts.append(label_full[len("option "):].strip())
        if value_part:
            parts.append(value_part)
    return parts


def _matches_reference_benchmark(answer: str, reference_answer: Optional[str]) -> Optional[bool]:
    if not reference_answer or not reference_answer.strip():
        return None
    ans_clean = answer.strip().lower()
    ref_clean = reference_answer.strip().lower()
    if ans_clean == ref_clean:
        return True

    ans_parts = _extract_option_parts(answer)
    ref_parts = _extract_option_parts(reference_answer)

    for a_part in ans_parts:
        for r_part in ref_parts:
            if a_part == r_part:
                return True
            try:
                a_num = float(re.sub(r"^[$€£₹]|%$", "", a_part).strip())
                r_num = float(re.sub(r"^[$€£₹]|%$", "", r_part).strip())
                if abs(a_num - r_num) <= max(1e-6, abs(r_num) * 0.02):
                    return True
            except ValueError:
                pass

    # Normalized token containment for free-form benchmark answers
    if len(ref_clean) >= 4 and (ref_clean in ans_clean or ans_clean in ref_clean):
        return True
    return False


def compute_answer_distributions(
    responses: List[StudentResponse],
    reference_answer: Optional[str] = None
) -> List[AnswerDistributionItem]:
    if not responses:
        return []

    total = len(responses)
    groups: Dict[str, List[int]] = defaultdict(list)
    for r in responses:
        ans = r.answer.strip()
        groups[ans].append(r.confidence)

    distributions: List[AnswerDistributionItem] = []

    for ans, conf_list in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(conf_list)
        pct = round((count / total) * 100, 1)
        avg_conf = round(sum(conf_list) / count, 2)
        is_correct = _matches_reference_benchmark(ans, reference_answer)
        distributions.append(AnswerDistributionItem(
            answer=ans,
            count=count,
            percentage=pct,
            average_confidence=avg_conf,
            is_reference_correct=is_correct,
        ))

    return distributions


def compute_confidence_distributions(
    responses: List[StudentResponse]
) -> List[ConfidenceDistributionItem]:
    total = len(responses)
    if total == 0:
        return [ConfidenceDistributionItem(confidence=i, count=0, percentage=0.0) for i in range(1, 6)]

    counts = {i: 0 for i in range(1, 6)}
    for r in responses:
        c = max(1, min(5, r.confidence))
        counts[c] += 1

    return [
        ConfidenceDistributionItem(
            confidence=i,
            count=counts[i],
            percentage=round((counts[i] / total) * 100, 1),
        )
        for i in range(1, 6)
    ]


def compute_belief_transitions(
    r1_responses: List[StudentResponse],
    r2_responses: List[StudentResponse]
) -> List[BeliefTransitionItem]:
    r1_map = {r.participant_id: r for r in r1_responses}
    r2_map = {r.participant_id: r for r in r2_responses}

    paired_ids = set(r1_map.keys()).intersection(set(r2_map.keys()))
    if not paired_ids:
        return []

    total_pairs = len(paired_ids)
    transitions: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {
        "count": 0,
        "init_conf": [],
        "rev_conf": [],
        "reasons": []
    })

    for pid in paired_ids:
        r1 = r1_map[pid]
        r2 = r2_map[pid]
        key = (r1.answer.strip(), r2.answer.strip())
        transitions[key]["count"] += 1
        transitions[key]["init_conf"].append(r1.confidence)
        transitions[key]["rev_conf"].append(r2.confidence)
        if r2.change_reason and r2.change_reason.strip():
            transitions[key]["reasons"].append(r2.change_reason.strip())

    items: List[BeliefTransitionItem] = []
    for (from_ans, to_ans), data in sorted(transitions.items(), key=lambda x: x[1]["count"], reverse=True):
        count = data["count"]
        pct = round((count / total_pairs) * 100, 1)
        avg_init = round(sum(data["init_conf"]) / count, 2)
        avg_rev = round(sum(data["rev_conf"]) / count, 2)
        sample_reasons = data["reasons"][:3]

        items.append(BeliefTransitionItem(
            from_answer=from_ans,
            to_answer=to_ans,
            count=count,
            percentage=pct,
            avg_initial_confidence=avg_init,
            avg_revised_confidence=avg_rev,
            sample_change_reasons=sample_reasons,
        ))

    return items


def generate_instructor_insight(
    question: Question,
    r1_dist: List[AnswerDistributionItem],
    r2_dist: List[AnswerDistributionItem],
    transitions: List[BeliefTransitionItem]
) -> str:
    insights = []

    # Round 1 insight
    if r1_dist:
        top_ans = r1_dist[0]
        if question.reference_answer and top_ans.is_reference_correct is False:
            insights.append(
                f"Attention: {top_ans.percentage}% of respondents selected '{top_ans.answer}' with a high average confidence of {top_ans.average_confidence}/5.0, indicating a persistent misconception."
            )
        elif question.question_type == QuestionType.SUBJECTIVE:
            if len(r1_dist) > 1 and r1_dist[1].percentage > 25:
                insights.append(
                    f"Polarized class: {top_ans.percentage}% favored '{top_ans.answer}' while {r1_dist[1].percentage}% favored '{r1_dist[1].answer}', showing fertile ground for opposing arguments."
                )

    # Transition insight
    if transitions:
        changed_count = sum(t.count for t in transitions if t.from_answer != t.to_answer)
        total_transitions = sum(t.count for t in transitions)
        if total_transitions > 0:
            change_rate = round((changed_count / total_transitions) * 100, 1)
            insights.append(
                f"Challenge Impact: {change_rate}% of students modified their position after the targeted challenge."
            )

    if not insights:
        return "Initial response collection underway. Baseline distributions recorded."

    return " | ".join(insights)


def get_aggregate_analysis(
    db: Session,
    question_id: str
) -> AggregateAnalysisResponse:
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return AggregateAnalysisResponse(question_id=question_id, round_1_total=0, round_2_total=0)

    r1_responses = (
        db.query(StudentResponse)
        .filter(StudentResponse.question_id == question_id, StudentResponse.round_number == 1)
        .all()
    )
    r2_responses = (
        db.query(StudentResponse)
        .filter(StudentResponse.question_id == question_id, StudentResponse.round_number == 2)
        .all()
    )

    r1_dist = compute_answer_distributions(r1_responses, question.reference_answer)
    r2_dist = compute_answer_distributions(r2_responses, question.reference_answer)

    conf1 = compute_confidence_distributions(r1_responses)
    conf2 = compute_confidence_distributions(r2_responses)

    transitions = compute_belief_transitions(r1_responses, r2_responses)
    insight = generate_instructor_insight(question, r1_dist, r2_dist, transitions)

    return AggregateAnalysisResponse(
        question_id=question_id,
        round_1_total=len(r1_responses),
        round_2_total=len(r2_responses),
        round_1_distributions=r1_dist,
        round_2_distributions=r2_dist,
        confidence_distributions_round_1=conf1,
        confidence_distributions_round_2=conf2,
        belief_transitions=transitions,
        instructor_insight=insight,
    )
