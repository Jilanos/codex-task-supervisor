from __future__ import annotations

import unittest

from codex_task_supervisor.similarity import recommend_model, task_similarity


def _features(task_type="implementation", domains=None, complexity="medium"):
    domains = domains or []
    return {
        "task_type": task_type,
        "domains": sorted(domains),
        "complexity_estimate": complexity,
    }


def _corpus_entry(task_type="implementation", domains=None, complexity="medium", model="gpt-a", effort="low", score=80.0):
    return {
        "task_id": "TASK-001",
        "plan_id": "PLAN-001",
        "features": _features(task_type, domains, complexity),
        "model": model,
        "reasoning_effort": effort,
        "final_score": score,
    }


class SimilarityTests(unittest.TestCase):
    def test_identical_features_score_one(self) -> None:
        f = _features("implementation", ["cli", "validation"], "medium")
        self.assertAlmostEqual(task_similarity(f, f), 1.0)

    def test_different_type_reduces_score(self) -> None:
        a = _features("implementation", ["cli"], "medium")
        b = _features("test", ["cli"], "medium")
        self.assertLess(task_similarity(a, b), task_similarity(a, a))

    def test_disjoint_domains_reduces_score(self) -> None:
        a = _features("implementation", ["cli", "validation"])
        b = _features("implementation", ["persistence", "api"])
        c = _features("implementation", ["cli", "validation"])
        self.assertLess(task_similarity(a, b), task_similarity(a, c))

    def test_empty_domains_both_score_max_domains(self) -> None:
        a = _features("implementation", [])
        b = _features("implementation", [])
        self.assertAlmostEqual(task_similarity(a, b), 1.0)

    def test_complexity_distance_reduces_score(self) -> None:
        a = _features("implementation", ["cli"], "low")
        b = _features("implementation", ["cli"], "high")
        c = _features("implementation", ["cli"], "low")
        self.assertLess(task_similarity(a, b), task_similarity(a, c))

    def test_score_in_unit_range(self) -> None:
        a = _features("implementation", ["cli", "tests"], "medium")
        b = _features("documentation", ["docs", "api"], "high")
        score = task_similarity(a, b)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class RecommendModelTests(unittest.TestCase):
    def test_returns_none_for_empty_corpus(self) -> None:
        self.assertIsNone(recommend_model(_features(), []))

    def test_returns_best_model_single_entry(self) -> None:
        corpus = [_corpus_entry(model="gpt-best", effort="medium", score=90.0)]
        result = recommend_model(_features(), corpus)
        self.assertEqual(result["recommended_model"], "gpt-best")
        self.assertEqual(result["reasoning_effort"], "medium")

    def test_prefers_higher_scoring_model_among_equals(self) -> None:
        query = _features("implementation", ["cli", "validation"])
        corpus = [
            _corpus_entry(task_type="implementation", domains=["cli", "validation"], model="gpt-good", effort="low", score=90.0),
            _corpus_entry(task_type="implementation", domains=["cli", "validation"], model="gpt-bad", effort="low", score=20.0),
        ]
        result = recommend_model(query, corpus)
        self.assertEqual(result["recommended_model"], "gpt-good")

    def test_top_k_limits_matches(self) -> None:
        corpus = [_corpus_entry(model=f"gpt-{i}", score=float(i * 10)) for i in range(10)]
        result = recommend_model(_features(), corpus, top_k=3)
        self.assertLessEqual(result["based_on"], 3)

    def test_result_has_required_keys(self) -> None:
        corpus = [_corpus_entry()]
        result = recommend_model(_features(), corpus)
        for key in ("recommended_model", "reasoning_effort", "confidence", "based_on", "top_matches"):
            self.assertIn(key, result)

    def test_confidence_in_unit_range(self) -> None:
        corpus = [_corpus_entry(model="a", score=80.0), _corpus_entry(model="b", score=60.0)]
        result = recommend_model(_features(), corpus)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_top_matches_contain_similarity_and_score(self) -> None:
        corpus = [_corpus_entry()]
        result = recommend_model(_features(), corpus)
        match = result["top_matches"][0]
        self.assertIn("similarity", match)
        self.assertIn("final_score", match)


if __name__ == "__main__":
    unittest.main()
