# Clone Verification Strategy - Design Document

## Overview

This document outlines approaches for verifying AI clone quality in YouTopia Mind. The core challenge: LLM responses are inherently non-deterministic, yet we need reliable ways to measure and improve clone accuracy.

## Your Current Architecture (Key Components)

| Component | What it does | Testability |
|-----------|--------------|-------------|
| `CloneVectorStore` | Clone-scoped vector retrieval | **Deterministic** |
| `RAGRetriever` | Retrieves + RL-boosts chunks | **Semi-deterministic** (RL scores change) |
| `PersonalityProfile` | Communication style, tone | **Deterministic** (extracted from data) |
| `PromptBuilder` | Constructs system + user prompts | **Deterministic** |
| `ChatService.generate()` | LLM response generation | **Non-deterministic** |

---

## Strategy 1: Decomposition Testing (Recommended First)

**Principle**: Test deterministic components separately from LLM generation.

### 1A. Retrieval Quality Tests

```python
# tests/test_retrieval_quality.py
def test_retrieval_returns_relevant_chunks():
    """Given a query, verify the right documents are retrieved."""
    # Setup: Upload known documents to test clone
    documents = [
        {"content": "I led the Q3 product launch...", "source": "work_history.txt"},
        {"content": "My favorite hobby is chess...", "source": "personal.txt"},
    ]

    # Test: Query about work should retrieve work document
    results = rag_retriever.retrieve("Tell me about product launches", top_k=3)

    # Assert: Work history doc should be #1
    assert "Q3 product launch" in results[0]["text"]
    assert results[0]["metadata"]["source"] == "work_history.txt"
```

**Metrics to track:**
- **Precision@K**: Of top K results, how many are relevant?
- **MRR (Mean Reciprocal Rank)**: How early does the first relevant result appear?
- **Source attribution accuracy**: Does the right document get retrieved?

### 1B. Prompt Construction Tests

```python
def test_prompt_includes_personality_traits():
    profile = PersonalityProfile(
        communication_style=CommunicationStyle(
            formality_level="casual",
            directness="direct"
        )
    )
    prompt = prompt_builder.build_system_prompt(profile)

    assert "casual" in prompt.lower()
    assert "direct" in prompt.lower()
```

### 1C. RL Score Boost Tests

```python
def test_positive_feedback_boosts_chunk_score():
    initial_score = chunk_score_service.get_score("chunk_hash_123")
    chunk_score_service.update_scores_from_feedback(
        clone_id=clone_id,
        rag_context={"chunks": [{"content": "test", "hash": "chunk_hash_123"}]},
        rating=1  # thumbs up
    )
    new_score = chunk_score_service.get_score("chunk_hash_123")
    assert new_score > initial_score
```

---

## Strategy 2: LLM-as-Judge Evaluation

**Principle**: Use a separate LLM to evaluate response quality against criteria.

### 2A. Personality Adherence Scoring

```python
def evaluate_personality_adherence(response: str, profile: PersonalityProfile) -> float:
    """Use GPT-4 to judge if response matches personality profile."""
    judge_prompt = f"""
    Rate how well this response matches the personality profile (1-5):

    Profile:
    - Formality: {profile.communication_style.formality_level}
    - Directness: {profile.communication_style.directness}
    - Sentence length avg: {profile.communication_style.sentence_length_avg}
    - Common phrases: {profile.communication_style.common_phrases}

    Response to evaluate:
    {response}

    Score (1-5) and brief explanation:
    """
    # Call judge LLM, parse score
```

### 2B. Factual Grounding Check

```python
def evaluate_grounding(response: str, rag_context: List[str]) -> dict:
    """Check if response is grounded in provided context."""
    judge_prompt = f"""
    Given this context:
    {rag_context}

    And this response:
    {response}

    Evaluate:
    1. Is the response factually grounded in the context? (yes/no)
    2. Does it hallucinate information not in context? (yes/no)
    3. Confidence score (0-1)
    """
```

### 2C. Hallucination Detection

```python
def detect_hallucination(response: str, source_docs: List[str]) -> List[str]:
    """Identify claims in response that aren't supported by source docs."""
    # Extract factual claims from response
    # Check each claim against source documents
    # Return unsupported claims
```

---

## Strategy 3: Golden Dataset Testing

**Principle**: Create curated test cases with expected behaviors.

### 3A. Test Case Structure

```python
@dataclass
class GoldenTestCase:
    id: str
    query: str
    expected_retrieval_sources: List[str]  # Which docs should be retrieved
    expected_response_traits: List[str]     # Keywords, tone markers
    forbidden_content: List[str]            # Should NOT appear in response
    personality_expectations: dict          # Formality, length, etc.
```

### 3B. Example Golden Dataset

```yaml
# tests/golden_dataset.yaml
test_cases:
  - id: "work_experience_query"
    query: "What was your biggest professional achievement?"
    expected_retrieval_sources: ["resume.pdf", "work_history.txt"]
    expected_response_traits: ["project", "led", "team", "result"]
    forbidden_content: ["I don't know", "As an AI"]
    personality_expectations:
      formality: "professional"
      min_length: 50
      max_length: 300

  - id: "personal_hobby_query"
    query: "What do you do for fun?"
    expected_retrieval_sources: ["personal.txt", "interests.md"]
    forbidden_content: ["professional", "work", "As an AI"]
```

### 3C. Semantic Similarity Regression

```python
def test_response_semantic_similarity():
    """Compare new response to baseline using embeddings."""
    baseline_response = "I led the Q3 product launch, increasing revenue by 40%..."
    new_response = chat_service.send_message("Tell me about your achievements")

    baseline_embedding = get_embedding(baseline_response)
    new_embedding = get_embedding(new_response)

    similarity = cosine_similarity(baseline_embedding, new_embedding)
    assert similarity > 0.7  # Should be semantically similar
```

---

## Strategy 4: Statistical Quality Metrics

**Principle**: Aggregate metrics over many interactions.

### 4A. Response Quality Dashboard

| Metric | How to Measure | Target |
|--------|---------------|--------|
| **Retrieval Precision@3** | % of top-3 chunks that are relevant | > 80% |
| **Personality Match Score** | LLM-judge rating (1-5) | > 4.0 |
| **Grounding Rate** | % of responses grounded in context | > 90% |
| **Hallucination Rate** | % of responses with ungrounded claims | < 5% |
| **User Feedback Rate** | thumbs_up / (thumbs_up + thumbs_down) | > 75% |
| **Response Length Variance** | Std dev from personality avg sentence length | Low |

### 4B. Tracking User Feedback (You Already Have This!)

Your `Message.feedback_rating` and `ChunkScoreService` already track this. Consider aggregating:

```sql
SELECT
    clone_id,
    AVG(CASE WHEN feedback_rating > 0 THEN 1 ELSE 0 END) as approval_rate,
    COUNT(*) as total_rated_messages
FROM messages
WHERE feedback_rating IS NOT NULL
GROUP BY clone_id;
```

---

## Strategy 5: Controlled Reproducibility

**Principle**: Make LLM calls as deterministic as possible for testing.

### 5A. Temperature = 0 for Tests

```python
# In test environment
llm_client = OpenAIClient(temperature=0)  # Deterministic mode
```

### 5B. Seed Parameter (if using OpenAI)

```python
response = openai.chat.completions.create(
    model="gpt-4",
    messages=messages,
    seed=12345,  # Same seed = same output (mostly)
    temperature=0
)
```

### 5C. Cache LLM Responses for Regression

```python
@pytest.fixture
def cached_llm_responses():
    """Load pre-recorded LLM responses for deterministic testing."""
    with open("tests/fixtures/llm_responses.json") as f:
        return json.load(f)

def test_with_cached_response(cached_llm_responses, mock_llm):
    mock_llm.return_value = cached_llm_responses["work_query"]
    # Test downstream logic with known response
```

---

## Trade-offs Summary

| Approach | Pros | Cons |
|----------|------|------|
| **Decomposition Testing** | Fully deterministic, fast, CI-friendly | Doesn't test end-to-end quality |
| **LLM-as-Judge** | Evaluates subjective quality, scalable | Costs money, judge can be wrong |
| **Golden Datasets** | Clear pass/fail, regression detection | Maintenance burden, brittle |
| **Statistical Metrics** | Real-world signal, production-focused | Slow feedback loop, noisy |
| **Temperature=0** | More reproducible | Not representative of production |

---

## Recommended Implementation Order

### Phase 1: Foundation (Low effort, high value)
1. Add retrieval quality tests (Precision@K)
2. Add prompt construction tests
3. Set `temperature=0` in test environment

### Phase 2: Quality Gates (Medium effort)
4. Create golden dataset (10-20 test cases per clone type)
5. Implement LLM-as-judge for personality adherence
6. Add semantic similarity regression tests

### Phase 3: Production Monitoring (Ongoing)
7. Dashboard tracking user feedback metrics
8. Hallucination detection on sampled responses
9. A/B testing framework for prompt/retrieval changes

---

## Your Three Verification Pillars

Based on your requirements:

| Pillar | What to Verify | Test Type |
|--------|---------------|-----------|
| **1. Retrieval + Source Usage** | Right docs retrieved, actually used in response | Deterministic + LLM-judge |
| **2. Calibration ("I don't know")** | Admits uncertainty when docs don't cover query | LLM-judge + Golden dataset |
| **3. Personality Matching** | Response sounds like the cloned person | LLM-judge + Statistical |

---

## CI Implementation Plan

### Test Suite Structure

```
tests/
├── unit/                          # Fast, deterministic
│   ├── test_retrieval.py          # Retrieval quality
│   ├── test_prompt_builder.py     # Prompt construction
│   └── test_chunk_scoring.py      # RL logic
├── integration/                   # Uses real embeddings, mock LLM
│   ├── test_rag_pipeline.py       # End-to-end retrieval
│   └── test_source_attribution.py # Source usage verification
├── evaluation/                    # LLM-as-judge (slower, costly)
│   ├── test_calibration.py        # "I don't know" behavior
│   ├── test_personality.py        # Personality adherence
│   └── test_grounding.py          # Hallucination detection
└── fixtures/
    ├── golden_dataset.yaml        # Expected behaviors
    └── personality_profiles.json  # Test personality data
```

### CI Pipeline Configuration

```yaml
# .github/workflows/clone-verification.yml
jobs:
  fast-tests:
    # Runs on every PR - < 2 minutes
    steps:
      - run: pytest tests/unit/ tests/integration/ -v

  evaluation-tests:
    # Runs on merge to main OR manually triggered
    # Uses LLM-as-judge - costs ~$0.50-2.00 per run
    if: github.ref == 'refs/heads/main'
    steps:
      - run: pytest tests/evaluation/ -v --tb=short
```

---

## Pillar 1: Retrieval + Source Usage Tests

### 1A. Retrieval Quality Test

```python
# tests/unit/test_retrieval.py
import pytest
from src.rag.retriever import RAGRetriever
from src.rag.clone_vector_store import CloneVectorStore

class TestRetrievalQuality:

    @pytest.fixture
    def seeded_clone(self, test_clone, test_documents):
        """Clone with known documents for testing."""
        vector_store = CloneVectorStore(test_clone.id, test_clone.tenant_id)
        vector_store.add_texts(
            texts=[doc["content"] for doc in test_documents],
            metadatas=[{"source": doc["source"]} for doc in test_documents]
        )
        return vector_store

    def test_relevant_query_retrieves_correct_source(self, seeded_clone):
        """Query about work should retrieve work documents."""
        retriever = RAGRetriever(clone_vector_store=seeded_clone)

        results = retriever.retrieve("product launch experience", top_k=3)

        sources = [r["metadata"]["source"] for r in results]
        assert "work_history.txt" in sources[:2], \
            f"Expected work_history.txt in top 2, got {sources}"

    def test_precision_at_k(self, seeded_clone, golden_queries):
        """Measure retrieval precision across golden dataset."""
        retriever = RAGRetriever(clone_vector_store=seeded_clone)
        precisions = []

        for case in golden_queries:
            results = retriever.retrieve(case["query"], top_k=3)
            retrieved_sources = {r["metadata"]["source"] for r in results}
            expected_sources = set(case["expected_sources"])

            precision = len(retrieved_sources & expected_sources) / 3
            precisions.append(precision)

        avg_precision = sum(precisions) / len(precisions)
        assert avg_precision >= 0.7, f"Precision@3 too low: {avg_precision:.2f}"
```

### 1B. Source Attribution Test

```python
# tests/integration/test_source_attribution.py

def test_response_uses_retrieved_context(mock_llm_client, seeded_clone):
    """Verify that retrieved context appears in the response."""
    chat_service = ChatService(clone_id, tenant_id, db)

    # Inject known context
    test_context = "I increased sales by 47% in Q3 2023"
    mock_rag_results = [{"text": test_context, "metadata": {"source": "sales.txt"}}]

    with patch.object(chat_service.rag_retriever, 'retrieve', return_value=mock_rag_results):
        response = chat_service.send_message(session_id, "What were your sales achievements?")

    # Check that key facts from context appear in response
    assert "47%" in response.content or "Q3 2023" in response.content, \
        "Response should reference context facts"
```

---

## Pillar 2: Calibration ("I Don't Know") Tests

### 2A. Out-of-Scope Query Detection

```python
# tests/evaluation/test_calibration.py

class TestCalibration:
    """Test that clone admits uncertainty appropriately."""

    # Queries about things NOT in any uploaded documents
    OUT_OF_SCOPE_QUERIES = [
        "What's your favorite restaurant in Tokyo?",
        "What do you think about quantum computing?",
        "Tell me about your childhood pet",
    ]

    UNCERTAINTY_MARKERS = [
        "I don't have information",
        "I'm not sure",
        "I don't recall",
        "I don't have specific",
        "Based on my available information",
        "I don't have details about",
    ]

    def test_admits_uncertainty_for_unknown_topics(self, chat_service):
        """Clone should express uncertainty for out-of-scope queries."""
        for query in self.OUT_OF_SCOPE_QUERIES:
            response = chat_service.send_message(session_id, query)

            has_uncertainty = any(
                marker.lower() in response.content.lower()
                for marker in self.UNCERTAINTY_MARKERS
            )

            # Also check with LLM judge for nuanced cases
            if not has_uncertainty:
                has_uncertainty = self._llm_judge_uncertainty(response.content, query)

            assert has_uncertainty, \
                f"Query '{query}' should trigger uncertainty, got: {response.content[:100]}"

    def _llm_judge_uncertainty(self, response: str, query: str) -> bool:
        """Use LLM to judge if response appropriately expresses uncertainty."""
        judge_prompt = f"""
        The user asked: "{query}"
        The AI responded: "{response}"

        Does the AI appropriately express uncertainty or admit it doesn't know,
        rather than making up information? Answer YES or NO.
        """
        result = judge_llm.generate(judge_prompt)
        return "YES" in result.upper()
```

### 2B. Hallucination Detection

```python
def test_no_hallucination_on_factual_queries(self, chat_service, seeded_clone):
    """Verify responses don't fabricate facts not in documents."""
    response = chat_service.send_message(
        session_id,
        "What specific projects did you work on at your last company?"
    )

    # Get the RAG context that was used
    rag_context = response.rag_context_json

    # Use LLM to check if all claims are grounded
    grounding_check = self._check_grounding(response.content, rag_context)

    assert grounding_check["is_grounded"], \
        f"Hallucinated claims: {grounding_check['ungrounded_claims']}"
```

---

## Pillar 3: Personality Matching Tests

### 3A. Style Consistency Check

```python
# tests/evaluation/test_personality.py

class TestPersonalityMatching:

    def test_formality_level_matches_profile(self, chat_service, personality_profile):
        """Response formality should match personality profile."""
        response = chat_service.send_message(session_id, "How would you approach a new project?")

        expected_formality = personality_profile.communication_style.formality_level

        judge_prompt = f"""
        Rate the formality of this text on a scale:
        1 = Very casual (slang, contractions, informal)
        3 = Neutral/balanced
        5 = Very formal (professional, no contractions)

        Text: "{response.content}"

        Score (1-5):
        """

        score = int(judge_llm.generate(judge_prompt).strip())

        expected_score = {"casual": 1, "medium": 3, "formal": 5}[expected_formality]
        assert abs(score - expected_score) <= 1, \
            f"Formality mismatch: expected ~{expected_score}, got {score}"

    def test_uses_characteristic_phrases(self, chat_service, personality_profile):
        """Response should occasionally use person's common phrases."""
        common_phrases = personality_profile.communication_style.common_phrases

        # Generate multiple responses
        responses = [
            chat_service.send_message(session_id, q)
            for q in ["Tell me about your work", "How do you solve problems?", "What motivates you?"]
        ]

        combined_text = " ".join(r.content for r in responses)

        # At least some common phrases should appear
        matches = sum(1 for phrase in common_phrases if phrase.lower() in combined_text.lower())

        assert matches >= 1, \
            f"Expected at least 1 common phrase from {common_phrases}, found none"

    def test_sentence_length_approximates_profile(self, chat_service, personality_profile):
        """Average sentence length should be close to profile."""
        response = chat_service.send_message(session_id, "Describe your professional philosophy")

        sentences = response.content.split('.')
        avg_length = sum(len(s.split()) for s in sentences if s.strip()) / len(sentences)

        expected_avg = personality_profile.communication_style.sentence_length_avg
        tolerance = expected_avg * 0.4  # 40% tolerance

        assert abs(avg_length - expected_avg) <= tolerance, \
            f"Sentence length {avg_length:.1f} too far from expected {expected_avg:.1f}"
```

### 3B. Personality Rubric Scoring

```python
def test_overall_personality_score(self, chat_service, personality_profile):
    """Comprehensive personality adherence check using LLM judge."""
    response = chat_service.send_message(
        session_id,
        "How do you typically handle disagreements at work?"
    )

    rubric = f"""
    Evaluate this response against the personality profile (1-5 scale):

    Profile:
    - Name: {personality_profile.person_name}
    - Formality: {personality_profile.communication_style.formality_level}
    - Directness: {personality_profile.communication_style.directness}
    - Detail level: {personality_profile.communication_style.detail_level}
    - Decision style: {personality_profile.communication_style.decision_making_style}
    - Dominant tone: {personality_profile.tone_characteristics}

    Response to evaluate:
    {response.content}

    Criteria:
    1. Does the tone match the profile? (1-5)
    2. Is the formality level appropriate? (1-5)
    3. Does it reflect the decision-making style? (1-5)
    4. Does it feel authentic to this person? (1-5)

    Average score (1-5):
    """

    score = float(judge_llm.generate(rubric).strip())
    assert score >= 3.5, f"Personality score too low: {score}"
```

---

## Golden Dataset Structure

```yaml
# tests/fixtures/golden_dataset.yaml

# Documents to seed in test clone
test_documents:
  - source: "work_history.txt"
    content: |
      I led the Q3 2023 product launch for our SaaS platform.
      Increased user adoption by 47% through targeted onboarding.
      Managed a team of 5 engineers and 2 designers.

  - source: "personal_interests.txt"
    content: |
      I enjoy playing chess and have competed in local tournaments.
      Reading science fiction is my favorite way to unwind.

# Test cases with expected behaviors
test_cases:
  # Should retrieve and use work content
  - id: "work_query"
    query: "Tell me about your product launch experience"
    expected_retrieval: ["work_history.txt"]
    expected_in_response: ["Q3", "product launch", "47%"]
    should_express_uncertainty: false

  # Should retrieve personal content
  - id: "hobby_query"
    query: "What do you do in your free time?"
    expected_retrieval: ["personal_interests.txt"]
    expected_in_response: ["chess", "reading"]
    should_express_uncertainty: false

  # Should express uncertainty - not in docs
  - id: "unknown_query"
    query: "What's your opinion on cryptocurrency?"
    expected_retrieval: []  # No relevant docs
    should_express_uncertainty: true
    forbidden_in_response: ["I believe", "My view is", "I think crypto"]

  # Should NOT hallucinate specific numbers
  - id: "specific_fact_query"
    query: "How many people were on your team?"
    expected_retrieval: ["work_history.txt"]
    expected_in_response: ["5", "engineers"]
    forbidden_in_response: ["10", "20", "large team"]  # Don't hallucinate
```

---

## Implementation Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `tests/conftest.py` | Modify | Add fixtures for test clones, golden dataset |
| `tests/unit/test_retrieval.py` | Create | Retrieval quality tests |
| `tests/integration/test_source_attribution.py` | Create | Source usage verification |
| `tests/evaluation/test_calibration.py` | Create | "I don't know" tests |
| `tests/evaluation/test_personality.py` | Create | Personality matching |
| `tests/fixtures/golden_dataset.yaml` | Create | Test cases and expected behaviors |
| `src/evaluation/llm_judge.py` | Create | LLM-as-judge utility |
| `.github/workflows/clone-verification.yml` | Create | CI pipeline |

---

## Cost Estimate for CI

| Test Type | Per Run | Monthly (50 PRs) |
|-----------|---------|------------------|
| Unit tests | $0 | $0 |
| Integration tests | $0.02 (embeddings) | $1 |
| Evaluation tests (LLM judge) | $0.50-1.00 | $25-50 |
| **Total** | ~$1 | ~$50 |

---

## Next Steps

1. Create test fixtures with golden dataset
2. Implement deterministic retrieval tests (unit/)
3. Add LLM judge utility for evaluation tests
4. Set up CI workflow with tiered testing
