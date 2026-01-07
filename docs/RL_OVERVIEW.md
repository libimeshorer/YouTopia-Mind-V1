# Reinforcement Learning System Overview

This document describes YouTopia Mind's reinforcement learning (RL) system that enables clones to learn from user feedback and improve over time.

## Table of Contents

1. [Current Implementation (Stage 1)](#current-implementation-stage-1)
2. [How It Works](#how-it-works)
3. [Design Decisions & Tradeoffs](#design-decisions--tradeoffs)
4. [Constants & Tuning Parameters](#constants--tuning-parameters)
5. [Future Roadmap](#future-roadmap)

---

## Current Implementation (Stage 1)

### What We're Building

**Global chunk scores** that learn from thumbs up/down feedback to improve RAG retrieval quality.

When users give feedback on clone responses:
- Chunks that appeared in positively-rated responses get **boosted** in future retrievals
- Chunks that appeared in negatively-rated responses get **demoted**
- This creates a flywheel: better chunks → better responses → more positive feedback → stronger boost

### Architecture

```
User Message
     ↓
[RAGRetriever.retrieve()] → Fetch 10 chunks from Pinecone
     ↓
[Load chunk_scores for clone] → {hash: score} map
     ↓
[Apply score boosts] → adjusted_score = similarity + (score * 0.3)
     ↓
[Re-rank, return top 5]
     ↓
[LLM generates response]
     ↓
[User gives thumbs up/down]
     ↓
[Update chunk_scores inline] → score = score * 0.9 + rating * 0.1
     ↓
[Next query uses updated scores]
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Migration | `alembic/versions/002_add_chunk_scores.py` | Creates `chunk_scores` table |
| Migration | `alembic/versions/003_add_enhanced_feedback.py` | Adds enhanced feedback columns |
| Model | `src/database/models.py` | `ChunkScore` + `Message` feedback fields |
| Service | `src/services/chunk_score_service.py` | Score updates (with weight support) |
| Retriever | `src/rag/retriever.py` | Applies score boosts during retrieval |
| Integration | `src/services/chat_service.py` | Enhanced feedback + RL score updates |
| API | `src/api/routers/chat.py` | Feedback endpoint with dual ratings |

---

## How It Works

### Scoring Algorithm: Exponential Moving Average (EMA)

```python
NEW_SCORE = OLD_SCORE * 0.9 + RATING * 0.1
```

Where:
- `RATING` is +1 (thumbs up) or -1 (thumbs down)
- `0.9` is the decay factor (history weight)
- `0.1` is the learning rate (new feedback weight)

**Why EMA?**
- Simple (one line vs complex algorithms)
- Naturally weights recent feedback higher
- Adapts to changing content quality over time
- No confidence thresholds needed

### Score Application

During retrieval, scores are applied as additive boosts:

```python
adjusted_score = base_similarity + (chunk_score * MAX_BOOST)
```

Where:
- `base_similarity` is the original Pinecone similarity (0.0 to 1.0)
- `chunk_score` is the learned score (-1.0 to +1.0)
- `MAX_BOOST` is 0.3 (caps the adjustment)

### Early Days Behavior

When no feedback exists for a clone:
1. `get_score_map()` returns an empty dictionary `{}`
2. The score boosting logic is **skipped entirely**
3. Retrieval works exactly as before (pure semantic similarity)
4. First feedback creates first score entry
5. Learning ramps up gradually as feedback accumulates

---

## Enhanced Feedback System

The feedback system supports dual-dimension ratings and differentiates between feedback sources.

### Feedback Dimensions

| Dimension | Who | Values | Purpose |
|-----------|-----|--------|---------|
| Content Rating | Everyone | -1, +1 | "Was this response helpful?" |
| Style Rating | Owner only | -1, 0, +1 | "Does this sound like me?" |
| Feedback Text | Everyone | Free text | Optional correction on negative feedback |

### Feedback Sources

Two feedback sources are tracked:

1. **Owner** (`feedback_source='owner'`):
   - The clone's creator/owner
   - Can rate both content AND style
   - Feedback weighted **2x** for chunk scoring
   - Most valuable signal for personalization
   - Uses authenticated `/chat/message/{id}/feedback` endpoint

2. **External User** (`feedback_source='external_user'`):
   - Someone chatting with the clone (e.g., colleague, customer)
   - Can rate content only
   - Feedback weighted **1x** for chunk scoring
   - Still valuable for content quality learning
   - TODO: Requires separate public endpoint (not yet implemented)

**Security Note:** `feedback_source` is derived server-side from authentication context, not from client request. The authenticated feedback endpoint always sets `feedback_source='owner'`.

### Owner 2x Weight

Owner feedback is weighted double because:
- Owners know what "good" looks like for their clone
- Owners are more invested in quality
- Style feedback is only available from owners

```python
# In ChunkScoreService.update_scores_from_feedback():
weight = 2.0 if feedback_source == 'owner' else 1.0
score = score * DECAY + rating * LEARNING_RATE * weight
```

### Duplicate Feedback Protection

Chunk scores are only updated on the **first** feedback submission for a message:

```python
# In ChatService.submit_feedback():
already_has_feedback = message.feedback_rating is not None
if already_has_feedback:
    # Update stored rating but skip RL update
    return message
```

**Why?** Without this protection:
1. User submits thumbs-up → chunks get +0.2
2. User changes to thumbs-down → chunks get another -0.2
3. Net effect: chunks were updated twice, scores don't reflect final rating

With protection: Re-submitting feedback updates the stored rating but doesn't re-update chunk scores. This prevents gaming (spam feedback) and accidental double-counting.

### Database Schema

```sql
-- Messages table additions (migration 003):
ALTER TABLE messages ADD COLUMN style_rating INTEGER;       -- -1, 0, 1, or NULL
ALTER TABLE messages ADD COLUMN feedback_source VARCHAR(20); -- 'owner' or 'external_user'
ALTER TABLE messages ADD COLUMN feedback_text TEXT;          -- Optional correction
```

### API Schema

```python
# Owner feedback endpoint: POST /chat/message/{id}/feedback
class SubmitFeedbackRequest(BaseModel):
    contentRating: int           # Required: -1 or 1
    styleRating: Optional[int]   # Optional: -1, 0, or 1
    feedbackText: Optional[str]  # Optional: correction text
    # Note: feedbackSource derived server-side (always 'owner' for this endpoint)
```

---

## Design Decisions & Tradeoffs

### Why One Table Instead of Multiple?

**Decision:** Single `chunk_scores` table vs separate feedback tracking + aggregation tables.

**Rationale:**
- No audit trail needed for MVP
- Scores update inline (no batch jobs)
- Simpler to understand and debug
- Can add columns later without migration pain

**Tradeoff:** We lose historical feedback details, but gain simplicity.

### Why Global Scores First?

**Decision:** Start with global chunk scores, defer context-aware scoring.

**Rationale:** With sparse feedback (~50 ratings), context-splitting dilutes signal:

```
Chunk A with 5 feedback signals:

Global approach:
  4 positive, 1 negative → score +0.6 (confident signal)

Context-split approach:
  "pricing" context: 2 positive → score +0.4 (weak)
  "technical" context: 2 positive, 1 negative → score +0.2 (noisy)
```

**Industry Standard:** Netflix, Spotify, and recommendation systems start with global signals and add context when data justifies it.

### Why Equal Attribution (No Position Weights)?

**Decision:** All chunks in a response share equal credit/blame.

**Alternatives considered:**
- Position weights (1.0, 0.8, 0.6, 0.4, 0.2 for ranks 1-5)
- First-chunk-only attribution

**Rationale:**
- User feedback is on the **whole response**, not individual chunks
- Position weights assume "top chunk contributed most" - not always true
- Equal attribution is simpler and empirically similar accuracy
- Can add position weights later if data shows they matter

### Why Inline Updates (No Scheduled Jobs)?

**Decision:** Update scores immediately when feedback is submitted.

**Rationale:**
- Simpler infrastructure (no cron, no Redis, no Celery)
- Immediate learning (next query benefits)
- Single database transaction
- No eventual consistency issues

**Tradeoff:** Slightly more work per feedback submission, but negligible.

---

## Constants & Tuning Parameters

### Learning Rate: 0.1

```python
NEW_SCORE = OLD_SCORE * 0.9 + RATING * 0.1
```

**What it means:**
- New feedback contributes 10% to the score
- Historical feedback contributes 90%
- Creates an effective window of ~10 recent feedbacks

**The math:**
| Feedbacks Ago | Influence Remaining |
|---------------|---------------------|
| 1 | 90% |
| 5 | 59% |
| 10 | 35% |
| 20 | 12% |

**Industry range:** 0.05 to 0.2
- **0.05** = Very slow learning, stable but slow to adapt
- **0.1** = Balanced (most common, our choice)
- **0.2** = Fast learning, adapts quickly but noisier

**When to adjust:**
- If learning seems too slow → increase to 0.15
- If scores are too volatile → decrease to 0.07

### Max Boost: 0.3

```python
adjusted_score = similarity + (chunk_score * 0.3)
```

**What it means:**
- A chunk with score +1.0 gets +0.3 boost
- A chunk with score -1.0 gets -0.3 penalty
- Similarity scores typically range 0.6-0.95

**Why 0.3?**

Example with different boost values:

| Chunk | Similarity | Score | Boost=0.1 | Boost=0.3 | Boost=0.5 |
|-------|------------|-------|-----------|-----------|-----------|
| A | 0.85 | +1.0 | 0.95 | **1.15→1.0** | 1.35→1.0 |
| B | 0.90 | -1.0 | 0.80 | **0.60** | 0.40 |
| C | 0.80 | 0.0 | 0.80 | **0.80** | 0.80 |

With boost=0.3:
- A beats B despite lower similarity (learning works!)
- Semantic relevance still matters (0.90 base vs 0.85)
- Scores don't completely override similarity

**When to adjust:**
- If re-ranking seems too aggressive → decrease to 0.2
- If learning impact is too weak → increase to 0.4

---

## Future Roadmap

### Stage 2: Intent Buckets (100+ feedback signals)

**Trigger:** Observing chunks with mixed feedback depending on query type.

**Implementation:**
```sql
ALTER TABLE chunk_scores ADD COLUMN intent VARCHAR(20) DEFAULT 'general';
```

```python
INTENTS = {
    'informational': ['what', 'who', 'explain', 'tell me'],
    'procedural': ['how', 'steps', 'guide', 'integrate'],
    'transactional': ['price', 'cost', 'buy', 'subscribe']
}
```

**How it works:**
1. Classify incoming query by intent
2. Store scores per (chunk, intent) pair
3. Apply boosts only from matching intent

### Stage 3: Style Learning (500+ feedback signals)

**Trigger:** After RAG quality learning is validated.

**Implementation:**
```sql
CREATE TABLE response_style_patterns (
    clone_id UUID,
    pattern_type VARCHAR(50),  -- 'length', 'formality', 'structure'
    pattern_key VARCHAR(50),   -- 'short', 'formal', 'bullet_points'
    preference_score FLOAT,
    PRIMARY KEY (clone_id, pattern_type, pattern_key)
);
```

**What it tracks:**
- Response length preference (short/medium/long)
- Formality level (casual/neutral/formal)
- Structure preference (narrative/bullet_points/numbered)

### Stage 4: Embedding Context (1000+ feedback signals)

**Trigger:** Need fine-grained context matching beyond simple intents.

**Implementation:**
```sql
ALTER TABLE chunk_scores ADD COLUMN query_embedding VECTOR(1536);
-- Requires pgvector extension
```

**How it works:**
1. Store query embedding with each feedback
2. When scoring, find feedback from similar queries
3. Weight scores by query similarity

### Stage 5: Fine-Tuning (10000+ signals, future)

**Potential approaches:**
- Collect (rejected, chosen) preference pairs
- Use OpenAI fine-tuning API
- Per-clone LoRA adapters

---

## Monitoring & Debugging

### Success Metrics

1. **Feedback rate**: % of responses receiving feedback (target: >10%)
2. **Positive ratio**: thumbs_up / (thumbs_up + thumbs_down) should increase
3. **Score distribution**: Scores should spread out (-0.5 to +0.5 range)
4. **Re-ranking impact**: How often do boosts change the top-5?

### Debugging Queries

```sql
-- View all scores for a clone
SELECT chunk_hash, score, hit_count
FROM chunk_scores
WHERE clone_id = 'your-clone-id'
ORDER BY score DESC;

-- Find chunks with most feedback
SELECT chunk_hash, score, hit_count
FROM chunk_scores
WHERE clone_id = 'your-clone-id'
ORDER BY hit_count DESC
LIMIT 20;

-- Distribution of scores
SELECT
    CASE
        WHEN score < -0.3 THEN 'very_negative'
        WHEN score < 0 THEN 'negative'
        WHEN score < 0.3 THEN 'positive'
        ELSE 'very_positive'
    END as bucket,
    COUNT(*) as count
FROM chunk_scores
WHERE clone_id = 'your-clone-id'
GROUP BY bucket;
```

### Log Markers

Look for these in application logs:
- `"boost_applied": 0.15` - Score boost was applied during retrieval
- `"chunk_scores_loaded": 42` - Number of scores loaded for clone
- `"score_updated"` - Score was updated after feedback
