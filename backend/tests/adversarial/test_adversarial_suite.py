"""Unit and integration tests for the 25 Adversarial Vectors."""
import pytest
from app.evaluation.adversarial_corpus import AdversarialCorpusRunner


def test_adversarial_corpus_survival():
    runner = AdversarialCorpusRunner()
    results = runner.run_all()

    assert len(results) == 25, f"Expected 25 adversarial test vectors, got {len(results)}"

    failed_vectors = [r for r in results if not r.defended]
    crashed_vectors = [r for r in results if r.http_actual == 500]

    assert len(crashed_vectors) == 0, f"Critical: {len(crashed_vectors)} attack vectors triggered HTTP 500: {[c.name for c in crashed_vectors]}"
    assert len(failed_vectors) == 0, f"{len(failed_vectors)} attack vectors breached defense: {[f.name for f in failed_vectors]}"

    for r in results:
        assert bool(r.defended) is True
        assert r.http_actual != 500
