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
        # Choose challenge type based on question type
        if question_type == "FACTUAL":
            ch_type = "COUNTEREXAMPLE"
            ch_text = (
                f"Consider an edge scenario related to: '{question_text}'. "
                f"What happens if one of the core assumptions is inverted? "
                f"Does your initial answer still hold true?"
            )
            targeted = "Over-generalization of standard rules without checking boundary constraints."
            learning_obj = accepted_reasoning or "Evaluate system behavior at boundary conditions and edge cases."
        elif question_type == "SUBJECTIVE":
            ch_type = "OPPOSING_ARGUMENTS"
            ch_text = (
                f"An experienced analyst argues the opposing position to the prevailing view. "
                f"They highlight critical trade-offs between short-term impact and systemic stability. "
                f"How would you refute or incorporate their argument?"
            )
            targeted = "Single-perspective evaluation overlooking conflicting trade-offs."
            learning_obj = accepted_reasoning or "Synthesize contrasting multi-stakeholder viewpoints."
        elif question_type == "PREDICTION":
            ch_type = "PREDICTION_REVEAL"
            ch_text = (
                f"Looking at how the overall class and market conditions typically behave: "
                f"How does an unexpected shift in group behavior alter your forecast?"
            )
            targeted = "Anchoring bias on baseline expectations."
            learning_obj = accepted_reasoning or "Adjust probabilistic predictions in response to dynamic distribution signals."
        else:
            ch_type = "TRANSFER_QUESTION"
            ch_text = (
                f"Apply the underlying principle of '{question_text}' to an adjacent domain: "
                f"If applied to a decentralized network, does the same logic lead to an equilibrium?"
            )
            targeted = "Context-bound reasoning."
            learning_obj = accepted_reasoning or "Transfer abstract causal mechanisms across domains."

        return {
            "challenge_type": ch_type,
            "challenge_text": ch_text,
            "targeted_reasoning_pattern": targeted,
            "relevance_evidence": f"Motivated by {len(distributions)} distinct answer clusters and observed justifications.",
            "learning_objective": learning_obj,
            "assumptions_and_uncertainties": "Assumes students understood the core terminology in the prompt.",
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

        prompt = f"""You are an expert pedagogical reasoning evaluator for a live university classroom platform (Belief Stress Test).

QUESTION DETAILS:
- Question Text: {question_text}
- Question Type: {question_type}
- Instructor Benchmark Answer (reference_answer): {reference_answer or 'None provided'}
- Instructor Benchmark Reasoning / Rubric (accepted_reasoning): {accepted_reasoning or 'None provided'}

EVALUATION RULES BY QUESTION TYPE:
1. If an Instructor Benchmark Answer (`reference_answer`) is provided, evaluate whether each student's `answer` matches it (exact match for Multiple Choice, numerical proximity for Prediction/Numeric, or semantic equivalence for Open-Ended text).
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
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data
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
        prompt = f"""You are designing a targeted live classroom challenge (Round 2 Belief Stress Test) to stress-test student reasoning without simply giving away the answer.

QUESTION DETAILS:
- Question: {question_text}
- Question Type: {question_type}
- Instructor Benchmark Answer: {reference_answer or 'None (subjective/exploratory)'}
- Instructor Benchmark Reasoning / Rubric: {accepted_reasoning or 'None provided'}

ROUND 1 ANSWER DISTRIBUTION:
{json.dumps(distributions, indent=2)}

EVALUATED STUDENT REASONING MODELS:
{json.dumps(categories, indent=2)}

TASK:
Select the best challenge strategy:
- COUNTEREXAMPLE (for FACTUAL / OPEN_REASONING misconceptions where students misapplied a rule or missed a boundary condition)
- OPPOSING_ARGUMENTS (for SUBJECTIVE questions where students ignored key trade-offs from the instructor rubric)
- PREDICTION_REVEAL (for PREDICTION questions to challenge flawed causal assumptions)
- TRANSFER_QUESTION (to test if students who gave surface explanations can apply the benchmark mechanism)

IMPORTANT: Do NOT explicitly state the final answer in `challenge_text`. Instead, pose a sharp Socratic counterexample, edge case, or contrasting scenario that exposes the flaw in the dominant misconception and guides students toward the instructor's benchmark reasoning.

Output MUST be valid JSON with this exact schema:
{{
  "challenge_type": "COUNTEREXAMPLE | OPPOSING_ARGUMENTS | PREDICTION_REVEAL | TRANSFER_QUESTION",
  "challenge_text": "The Socratic challenge prompt students will read in Round 2",
  "targeted_reasoning_pattern": "Which specific student misconception or mental model this challenges",
  "relevance_evidence": "Why this challenge directly addresses the observed Round 1 answers and explanations",
  "learning_objective": "What benchmark insight students should discover",
  "assumptions_and_uncertainties": "Any caveats or edge assumptions"
}}"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data
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
Summarize the outcomes of a two-round Belief Stress Test:
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
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
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
