"""Task similarity scoring for model recommendation.

Computes a weighted similarity score between a query task's feature vector
and a corpus of evaluated reference tasks, then recommends the model that
performed best on the most similar reference tasks.
"""

from __future__ import annotations

from typing import Any


_COMPLEXITY_RANK = {"low": 0, "medium": 1, "high": 2}

# Weights must sum to 1.0
_W_DOMAINS = 0.50
_W_TYPE = 0.30
_W_COMPLEXITY = 0.20


def task_similarity(query: dict[str, Any], reference: dict[str, Any]) -> float:
    """Return a similarity score in [0, 1] between two feature vectors."""
    domain_score = _jaccard(
        set(query.get("domains") or []),
        set(reference.get("domains") or []),
    )
    type_score = 1.0 if query.get("task_type") == reference.get("task_type") else 0.0
    complexity_score = _complexity_similarity(
        query.get("complexity_estimate", "medium"),
        reference.get("complexity_estimate", "medium"),
    )
    return _W_DOMAINS * domain_score + _W_TYPE * type_score + _W_COMPLEXITY * complexity_score


def recommend_model(
    query_features: dict[str, Any],
    corpus: list[dict[str, Any]],
    top_k: int = 5,
) -> dict[str, Any] | None:
    """Return the recommended model/effort based on nearest-neighbour voting.

    Each corpus entry must have:
      features (dict), model (str), reasoning_effort (str), final_score (float)

    Returns a dict with:
      recommended_model, reasoning_effort, confidence, based_on, top_matches
    or None if the corpus is empty.
    """
    if not corpus:
        return None

    scored = []
    for entry in corpus:
        ref_features = entry.get("features") or {}
        sim = task_similarity(query_features, ref_features)
        scored.append({
            "similarity": sim,
            "model": entry["model"],
            "reasoning_effort": entry["reasoning_effort"],
            "final_score": entry["final_score"],
            "task_id": entry.get("task_id", ""),
            "plan_id": entry.get("plan_id", ""),
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top = scored[:top_k]

    # Weighted vote: weight = similarity × normalized_final_score
    votes: dict[tuple[str, str], float] = {}
    for match in top:
        key = (match["model"], match["reasoning_effort"])
        weight = match["similarity"] * (match["final_score"] / 100.0)
        votes[key] = votes.get(key, 0.0) + weight

    if not votes:
        return None

    best_key = max(votes, key=lambda k: votes[k])
    total_weight = sum(votes.values())
    confidence = votes[best_key] / total_weight if total_weight > 0 else 0.0

    return {
        "recommended_model": best_key[0],
        "reasoning_effort": best_key[1],
        "confidence": round(confidence, 4),
        "based_on": len(top),
        "top_matches": [
            {
                "task_id": m["task_id"],
                "plan_id": m["plan_id"],
                "model": m["model"],
                "reasoning_effort": m["reasoning_effort"],
                "similarity": round(m["similarity"], 4),
                "final_score": m["final_score"],
            }
            for m in top
        ],
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _complexity_similarity(a: str, b: str) -> float:
    ra = _COMPLEXITY_RANK.get(a, 1)
    rb = _COMPLEXITY_RANK.get(b, 1)
    return 1.0 - abs(ra - rb) / 2.0
