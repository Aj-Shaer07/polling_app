import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    @abstractmethod
    def analyze_responses(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        responses_data: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze anonymized student responses and semantic clusters against the
        instructor benchmark (reference_answer & accepted_reasoning).
        Returns evaluated reasoning categories with mapped response_indices.
        """
        pass

    @abstractmethod
    def generate_challenge(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        categories: List[Dict[str, Any]],
        distributions: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a targeted challenge proposal based on observed reasoning patterns
        and instructor benchmark.
        """
        pass

    @abstractmethod
    def summarize_results(
        self,
        question_text: str,
        aggregates: Dict[str, Any],
        categories: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Summarize final results, transitions, and instructional takeaways.
        """
        pass


class MockAIProvider(AIProvider):
    """
    Deterministic, reliable local provider for testing, offline development,
    and automatic fail-safe fallback when LLM API keys are absent or rate-limited.
    Evaluates answers and explanations against reference_answer and accepted_reasoning.
    """

    def analyze_responses(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        responses_data: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.services.aggregation import _matches_reference_benchmark

        categories = []
        ref_keywords = [
            w.lower().strip(".,;:!?()[]\"'")
            for w in (accepted_reasoning or "").split()
            if len(w.strip(".,;:!?()[]\"'")) >= 4
        ]

        if reference_answer or accepted_reasoning:
            aligned_indices = []
            partial_indices = []
            misconception_indices = []

            for idx, r in enumerate(responses_data):
                ans = str(r.get("answer") or "")
                exp = str(r.get("explanation") or "").lower()
                ans_matches = _matches_reference_benchmark(ans, reference_answer) if reference_answer else True
                reasoning_matches = (
                    any(kw in exp for kw in ref_keywords)
                    if ref_keywords and exp
                    else bool(exp)
                )

                if ans_matches and reasoning_matches:
                    aligned_indices.append(idx)
                elif ans_matches and not reasoning_matches:
                    partial_indices.append(idx)
                else:
                    misconception_indices.append(idx)

            if aligned_indices:
                categories.append({
                    "title": "Benchmark-Aligned Reasoning",
                    "description": (
                        "Answer and conceptual explanation align with the instructor benchmark"
                        + (f" ({accepted_reasoning[:80]})." if accepted_reasoning else ".")
                    ),
                    "is_misconception": False,
                    "sample_explanations": [
                        responses_data[i].get("explanation", "")
                        for i in aligned_indices
                        if responses_data[i].get("explanation")
                    ][:3],
                    "response_indices": aligned_indices,
                })
            if partial_indices:
                categories.append({
                    "title": "Correct Answer with Incomplete / Surface Intuition",
                    "description": "Reached the target answer but explanation omits key benchmark mechanisms or relies on heuristic guessing.",
                    "is_misconception": True,
                    "sample_explanations": [
                        responses_data[i].get("explanation", "")
                        for i in partial_indices
                        if responses_data[i].get("explanation")
                    ][:3],
                    "response_indices": partial_indices,
                })
            if misconception_indices:
                categories.append({
                    "title": "Divergent / Misconception Model",
                    "description": "Answer and/or underlying causal reasoning diverge from the instructor benchmark.",
                    "is_misconception": True,
                    "sample_explanations": [
                        responses_data[i].get("explanation", "")
                        for i in misconception_indices
                        if responses_data[i].get("explanation")
                    ][:3],
                    "response_indices": misconception_indices,
                })

        if not categories:
            if clusters:
                for idx, c in enumerate(clusters):
                    sample_quotes = c.get("sample_quotes", [])
                    kw = ", ".join(c.get("keywords", [])) or "general"
                    categories.append({
                        "title": f"Pattern {idx + 1}: {kw.title()} rationale",
                        "description": f"Students emphasized {kw} in their reasoning.",
                        "is_misconception": False,
                        "sample_explanations": sample_quotes[:3],
                        "cluster_id": c.get("cluster_id", idx),
                    })
            else:
                categories.append({
                    "title": "Baseline Intuition",
                    "description": "General intuitive response based on standard classroom framing.",
                    "is_misconception": False,
                    "sample_explanations": [r.get("explanation", "") for r in responses_data if r.get("explanation")][:2],
                    "response_indices": list(range(len(responses_data))),
                })

        return {
            "categories": categories,
            "common_viewpoints": ["Students grouped by benchmark alignment and reasoning mental models."],
            "uncertainty_flags": [],
            "summary": "Evaluated student answers and explanations against instructor benchmark and grouped into reasoning models.",
        }

    def generate_challenge(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        categories: List[Dict[str, Any]],
        distributions: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        top_ans = distributions[0].get("answer", "") if distributions else ""
        top_pct = distributions[0].get("percentage", 0) if distributions else 0
        top_conf = distributions[0].get("average_confidence", 0) if distributions else 0
        second_ans = distributions[1].get("answer", "") if len(distributions) > 1 else ""
        second_pct = distributions[1].get("percentage", 0) if len(distributions) > 1 else 0

        wrong_dists = [d for d in distributions if d.get("is_reference_correct") is False]
        sample_quote = ""
        for cat in categories:
            quotes = cat.get("sample_explanations") or []
            if quotes and isinstance(quotes[0], str) and quotes[0].strip():
                sample_quote = quotes[0].strip()
                if cat.get("is_misconception"):
                    break

        quote_clause = (
            f" One student reasoned: \"{sample_quote[:120]}\"."
            if sample_quote
            else ""
        )
        rubric_clause = (
            f" Keeping the core requirement in mind ({accepted_reasoning}),"
            if accepted_reasoning
            else ""
        )

        # Choose challenge type and build a question-specific challenge from Round 1 data
        if question_type == "FACTUAL":
            ch_type = "COUNTEREXAMPLE"
            if len(distributions) > 1 and second_ans:
                ch_text = (
                    f"In Round 1 on '{question_text}', the class split between '{top_ans}' ({top_pct}%) "
                    f"and '{second_ans}' ({second_pct}%).{quote_clause}{rubric_clause} "
                    f"Walk through '{question_text}' step by step: which of these two options strictly satisfies "
                    f"every part of the question, and where does the other option's calculation or assumption break down?"
                )
            elif wrong_dists:
                w_ans = wrong_dists[0].get("answer", top_ans)
                ch_text = (
                    f"In Round 1 on '{question_text}', {wrong_dists[0].get('percentage', top_pct)}% selected '{w_ans}' "
                    f"(avg confidence {wrong_dists[0].get('average_confidence', top_conf)}/5).{quote_clause}{rubric_clause} "
                    f"Re-verify '{question_text}' step by step from the original values/conditions — does '{w_ans}' "
                    f"actually hold when you check each step, or must you revise your answer?"
                )
            elif top_ans:
                ch_text = (
                    f"For '{question_text}', {top_pct}% of respondents selected '{top_ans}' in Round 1.{quote_clause}"
                    f"{rubric_clause} Before locking in your final Round 2 answer, verify each step of '{question_text}' "
                    f"and explain why the remaining choices can be ruled out."
                )
            else:
                ch_text = (
                    f"Re-examine the initial question '{question_text}'.{rubric_clause} "
                    f"Verify each step of your derivation before submitting your Round 2 answer."
                )
            targeted = (
                f"Competing Round 1 answers ('{top_ans}' vs '{second_ans}')"
                if second_ans
                else f"Verification of Round 1 reasoning on '{question_text}'"
            )
            learning_obj = accepted_reasoning or f"Verify step-by-step accuracy on '{question_text}'."
        elif question_type == "SUBJECTIVE":
            ch_type = "OPPOSING_ARGUMENTS"
            if len(distributions) > 1 and second_ans:
                ch_text = (
                    f"On '{question_text}', {top_pct}% favored '{top_ans}' while {second_pct}% favored '{second_ans}'."
                    f"{quote_clause}{rubric_clause} Suppose a peer defends the opposing choice against yours — "
                    f"what is the strongest counterargument from '{question_text}' that could make you revise or refine your position?"
                )
            else:
                ch_text = (
                    f"On '{question_text}', most respondents converged on '{top_ans or 'a single viewpoint'}'."
                    f"{quote_clause}{rubric_clause} Consider the strongest counter-perspective to your Round 1 choice: "
                    f"what key trade-off in '{question_text}' did your initial explanation overlook?"
                )
            targeted = "Single-perspective evaluation overlooking competing trade-offs in the initial question."
            learning_obj = accepted_reasoning or f"Synthesize contrasting viewpoints on '{question_text}'."
        elif question_type == "PREDICTION":
            ch_type = "PREDICTION_REVEAL"
            if len(distributions) > 1 and second_ans:
                ch_text = (
                    f"For '{question_text}', Round 1 estimates centered around '{top_ans}' ({top_pct}%) and "
                    f"'{second_ans}' ({second_pct}%).{quote_clause}{rubric_clause} "
                    f"Given how the rest of the class estimated '{question_text}', re-check your quantitative calculation — "
                    f"would you revise your numerical prediction?"
                )
            else:
                ch_text = (
                    f"For '{question_text}', the leading Round 1 prediction was '{top_ans}' ({top_pct}%)."
                    f"{quote_clause}{rubric_clause} Re-compute the expected value directly from '{question_text}' — "
                    f"does your initial numerical estimate still hold?"
                )
            targeted = f"Quantitative calibration on '{question_text}'."
            learning_obj = accepted_reasoning or f"Calibrate quantitative predictions for '{question_text}'."
        else:
            ch_type = "TRANSFER_QUESTION"
            ch_text = (
                f"Reviewing your Round 1 explanation for '{question_text}'{(' (' + top_ans + ')') if top_ans else ''}:"
                f"{quote_clause}{rubric_clause} Test whether your Round 1 reasoning strictly answers every part of "
                f"'{question_text}' without unstated assumptions — how would you strengthen or revise your response?"
            )
            targeted = f"Completeness of causal explanation for '{question_text}'."
            learning_obj = accepted_reasoning or f"Articulate complete step-by-step reasoning for '{question_text}'."

        return {
            "challenge_type": ch_type,
            "challenge_text": ch_text,
            "targeted_reasoning_pattern": targeted,
            "relevance_evidence": f"Derived from {len(distributions)} Round 1 answer group(s) on '{question_text}'.",
            "learning_objective": learning_obj,
            "assumptions_and_uncertainties": "Directly anchored to the initial question and Round 1 class responses.",
        }

    def summarize_results(
        self,
        question_text: str,
        aggregates: Dict[str, Any],
        categories: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "summary": "Completed two rounds of inquiry. Observed noticeable convergence toward verified concepts after the targeted challenge.",
            "recommended_actions": [
                "Review the most common transition pathway on the blackboard.",
                "Reinforce boundary conditions that distinguish the correct solution.",
            ]
        }


class GeminiProvider(AIProvider):
    """
    Official Gemini API Provider utilizing Google GenAI SDK (`google-genai`).
    Evaluates student answers and written reasoning against the professor's
    benchmark (reference_answer & accepted_reasoning) and groups students by
    their conceptual mental model.
    """

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model = model
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.fallback = MockAIProvider()

    @staticmethod
    def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
        text = (raw_text or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def _call_gemini_json(self, prompt: str) -> Dict[str, Any]:
        candidate_models = []
        for m in [self.model, "gemini-3.8-flash", "gemini-3.5-flash-lite"]:
            if m and m not in candidate_models:
                candidate_models.append(m)

        last_err: Optional[Exception] = None

        # 1. Try Interactions API if supported by installed google-genai SDK
        if hasattr(self.client, "interactions"):
            for m in candidate_models:
                try:
                    interaction = self.client.interactions.create(
                        model=m,
                        input=prompt,
                    )
                    out_text = getattr(interaction, "output_text", None)
                    if not out_text and getattr(interaction, "steps", None):
                        for step in reversed(interaction.steps):
                            if getattr(step, "content", None):
                                for part in step.content:
                                    if getattr(part, "text", None):
                                        out_text = part.text
                                        break
                            if out_text:
                                break
                    if out_text:
                        return self._clean_and_parse_json(out_text)
                except Exception as e:
                    last_err = e

        # 2. Try standard models.generate_content API
        for m in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                if response and response.text:
                    return self._clean_and_parse_json(response.text)
            except Exception as e:
                last_err = e

        raise RuntimeError(f"All Gemini API calls failed: {last_err}")

    def analyze_responses(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        responses_data: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        indexed_submissions = [
            {
                "response_index": idx,
                "answer": r.get("answer"),
                "explanation": r.get("explanation") or "(No written explanation)",
                "confidence": r.get("confidence"),
            }
            for idx, r in enumerate(responses_data)
        ]

        prompt = f"""You are an expert pedagogical reasoning evaluator for a live university classroom platform (Class Polling App).

QUESTION DETAILS:
- Question Text: {question_text}
- Question Type: {question_type}
- Instructor Benchmark Answer (reference_answer): {reference_answer or 'None provided'}
- Instructor Benchmark Reasoning / Rubric (accepted_reasoning): {accepted_reasoning or 'None provided'}

EVALUATION RULES BY QUESTION TYPE:
1. If an Instructor Benchmark Answer (`reference_answer`) is provided, evaluate whether each student's `answer` matches it (exact match or option-value match for Multiple Choice, numerical proximity for Prediction/Numeric, or semantic equivalence for Open-Ended text).
2. Always evaluate each student's written `explanation` against the Instructor Benchmark Reasoning (`accepted_reasoning`) and core domain logic:
   - Identify students who have BOTH the benchmark-aligned answer AND sound benchmark-aligned reasoning (`is_misconception`: false).
   - Identify students who arrived at the right answer for the WRONG or superficial reason (`is_misconception`: true).
   - Identify students who hold specific conceptual misconceptions, flawed derivations, or one-sided blind spots (`is_misconception`: true for FACTUAL/PREDICTION/OPEN_REASONING, or competing viewpoint groups for SUBJECTIVE).
3. Group ALL student submissions (by their `response_index` from 0 to {max(0, len(indexed_submissions) - 1)}) into 2 to 4 distinct reasoning categories / mental models so every student is assigned to a category.

PRE-COMPUTED SEMANTIC CLUSTERS (TF-IDF + KMeans):
{json.dumps(clusters, indent=2)}

ANONYMIZED STUDENT SUBMISSIONS:
{json.dumps(indexed_submissions, indent=2)}

Output MUST be valid JSON matching this exact schema:
{{
  "categories": [
    {{
      "title": "Short descriptive mental model / reasoning category title",
      "description": "Evaluation of how this group's answer and reasoning compare to the instructor benchmark",
      "is_misconception": true,
      "sample_explanations": ["verbatim student quote 1", "verbatim student quote 2"],
      "response_indices": [0, 2]
    }}
  ],
  "common_viewpoints": ["Key insight 1"],
  "uncertainty_flags": [],
  "summary": "Concise synthesis of class alignment with the instructor benchmark and primary misconceptions"
}}"""
        try:
            return self._call_gemini_json(prompt)
        except Exception as e:
            logger.warning(f"GeminiProvider.analyze_responses failed: {e}. Falling back to mock provider.")
            return self.fallback.analyze_responses(
                question_text, question_type, reference_answer, responses_data, clusters, accepted_reasoning
            )

    def generate_challenge(
        self,
        question_text: str,
        question_type: str,
        reference_answer: Optional[str],
        categories: List[Dict[str, Any]],
        distributions: List[Dict[str, Any]],
        accepted_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = f"""You are designing a targeted Round 2 classroom challenge for the Class Polling App that is directly derived from the initial question and the class's Round 1 submissions.

INITIAL QUESTION DETAILS:
- Initial Question: {question_text}
- Question Type: {question_type}
- Instructor Benchmark Answer: {reference_answer or 'None (subjective/exploratory)'}
- Instructor Benchmark Reasoning / Rubric: {accepted_reasoning or 'None provided'}

ROUND 1 ANSWER DISTRIBUTION:
{json.dumps(distributions, indent=2)}

EVALUATED ROUND 1 STUDENT REASONING MODELS:
{json.dumps(categories, indent=2)}

TASK:
1. Build a Round 2 challenge directly anchored to the initial question ("{question_text}") and the specific answers/explanations students submitted in Round 1.
2. Directly reference the competing options or misconception reasoning observed in Round 1 (for example, contrasting the top answers chosen by the class or questioning a flawed step in their explanation) and ask a sharp follow-up challenge on the initial question that makes students test and verify their Round 1 answer.
3. IMPORTANT: Do NOT explicitly reveal which option is the final correct answer in `challenge_text`. Instead, challenge the flaw in the misconception so students must re-evaluate the initial question themselves.

Select the best `challenge_type`:
- COUNTEREXAMPLE (for FACTUAL / OPEN_REASONING questions)
- OPPOSING_ARGUMENTS (for SUBJECTIVE questions)
- PREDICTION_REVEAL (for PREDICTION questions)
- TRANSFER_QUESTION (for testing whether surface explanations hold up)

Output MUST be valid JSON with this exact schema:
{{
  "challenge_type": "COUNTEREXAMPLE | OPPOSING_ARGUMENTS | PREDICTION_REVEAL | TRANSFER_QUESTION",
  "challenge_text": "The direct question-specific Socratic challenge prompt students will read in Round 2",
  "targeted_reasoning_pattern": "Which specific Round 1 student misconception or answer split this challenges",
  "relevance_evidence": "How this challenge directly references the initial question and observed Round 1 answers",
  "learning_objective": "What benchmark insight students should discover",
  "assumptions_and_uncertainties": "Any caveats or edge assumptions"
}}"""
        try:
            return self._call_gemini_json(prompt)
        except Exception as e:
            logger.warning(f"GeminiProvider.generate_challenge failed: {e}. Falling back to mock provider.")
            return self.fallback.generate_challenge(
                question_text, question_type, reference_answer, categories, distributions, accepted_reasoning
            )

    def summarize_results(
        self,
        question_text: str,
        aggregates: Dict[str, Any],
        categories: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = f"""
Summarize the outcomes of a two-round Class Polling App diagnostic question:
Question: {question_text}
Aggregates: {json.dumps(aggregates, indent=2)}
Belief Transitions: {json.dumps(transitions, indent=2)}

Output MUST be valid JSON:
{{
  "summary": "Concise summary of student progression",
  "recommended_actions": ["Action 1", "Action 2"]
}}
"""
        try:
            return self._call_gemini_json(prompt)
        except Exception as e:
            logger.warning(f"GeminiProvider.summarize_results failed: {e}. Falling back.")
            return self.fallback.summarize_results(question_text, aggregates, categories, transitions)


def get_ai_provider() -> AIProvider:
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
        try:
            return GeminiProvider(api_key=settings.GEMINI_API_KEY.strip(), model=settings.GEMINI_MODEL)
        except Exception as e:
            logger.warning(f"Failed to instantiate GeminiProvider: {e}. Using MockAIProvider.")
            return MockAIProvider()
    return MockAIProvider()
