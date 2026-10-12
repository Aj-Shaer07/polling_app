from app.services.llm_provider import MockAIProvider
from app.services.text_analysis import cluster_explanations
from app.services.aggregation import _matches_reference_benchmark


def test_mock_ai_provider_question_types():
    provider = MockAIProvider()

    # 1. Factual question -> Counterexample challenge directly referencing question & Round 1 split
    fact_ch = provider.generate_challenge(
        question_text="Is it optimal to bid higher than your valuation in Vickrey auctions?",
        question_type="FACTUAL",
        reference_answer="No",
        categories=[{"title": "Greedy bidding", "description": "Trying to guarantee a win"}],
        distributions=[{"answer": "Yes", "count": 25, "percentage": 55.6}, {"answer": "No", "count": 20, "percentage": 44.4}],
    )
    assert fact_ch["challenge_type"] == "COUNTEREXAMPLE"
    assert "vickrey auctions" in fact_ch["challenge_text"].lower()
    assert "'yes'" in fact_ch["challenge_text"].lower()

    # 2. Subjective question -> Opposing arguments challenge referencing question & choices
    subj_ch = provider.generate_challenge(
        question_text="Should algorithmic trading speed be capped by financial regulators?",
        question_type="SUBJECTIVE",
        reference_answer=None,
        categories=[{"title": "Pro-regulation", "description": "Market stability concerns"}],
        distributions=[{"answer": "Yes", "count": 22, "percentage": 48.9}, {"answer": "No", "count": 23, "percentage": 51.1}],
    )
    assert subj_ch["challenge_type"] == "OPPOSING_ARGUMENTS"
    assert "algorithmic trading speed" in subj_ch["challenge_text"].lower()

    # 3. Prediction question -> Prediction reveal challenge
    pred_ch = provider.generate_challenge(
        question_text="What percentage of market participants will default in stress condition X?",
        question_type="PREDICTION",
        reference_answer=None,
        categories=[],
        distributions=[],
    )
    assert pred_ch["challenge_type"] == "PREDICTION_REVEAL"

    # 4. Open reasoning -> Transfer question
    open_ch = provider.generate_challenge(
        question_text="Explain the Nash Equilibrium in this asymmetric game.",
        question_type="OPEN_REASONING",
        reference_answer="Player 1 plays A, Player 2 plays B",
        categories=[],
        distributions=[],
    )
    assert open_ch["challenge_type"] == "TRANSFER_QUESTION"


def test_mcq_option_benchmark_matching():
    assert _matches_reference_benchmark("Option A: 6", "6") is True
    assert _matches_reference_benchmark("Option A: 6", "Option A") is True
    assert _matches_reference_benchmark("Option A: 6", "Option A: 6") is True
    assert _matches_reference_benchmark("Option C: 12", "6") is False
    assert _matches_reference_benchmark("Option B: 4", "6") is False


def test_explanation_clustering_service():
    explanations = [
        "I bid higher because I want to guarantee winning the prize at any cost.",
        "Bidding above valuation ensures a win since second price is paid anyway.",
        "I bid high to win the item regardless of others.",
        "I bid exactly what it's worth to avoid paying more than my value.",
        "Honest bidding is a weakly dominant strategy.",
        "Truthful bidding protects against overpaying if someone bids high.",
    ]
    clusters = cluster_explanations(explanations, max_clusters=3)
    assert len(clusters) >= 1
    for c in clusters:
        assert "sample_quotes" in c
        assert "keywords" in c
        assert c["count"] > 0


def test_clustering_empty_and_sparse_fallback():
    # Empty list
    assert cluster_explanations([]) == []
    # Single item
    res = cluster_explanations(["Just one explanation"])
    assert len(res) == 1
    assert res[0]["count"] == 1
