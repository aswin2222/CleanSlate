#!/usr/bin/env python3
"""Adversarial Corpus Generator and Robustness Verifier.

Executes all 25 adversarial test vectors against CleanSlate, persists the
corpus test summary artifact, and verifies zero HTTP 500s and 100% defense.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure backend modules can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.evaluation.adversarial_corpus import AdversarialCorpusRunner


def main() -> int:
    print("=" * 80)
    print("  CLEANSLATE ADVERSARIAL CORPUS: 25 ATTACK VECTOR VERIFICATION")
    print("=" * 80)

    runner = AdversarialCorpusRunner()
    results = runner.run_all()

    print(f"Total Vectors Evaluated: {len(results)}")
    print(f"{'Vector ID':<10} | {'Category':<22} | {'Name':<32} | {'Defended':<8} | {'HTTP'}")
    print("-" * 80)

    failed = []
    crashed = []

    for r in results:
        status_str = "PASS" if r.defended else "FAIL"
        print(f"{r.vector_id:<10} | {r.category:<22} | {r.name[:32]:<32} | {status_str:<8} | {r.http_actual}")
        if not r.defended:
            failed.append(r)
        if r.http_actual == 500:
            crashed.append(r)

    print("-" * 80)

    # Persist summary artifact
    out_dir = REPO_ROOT / "data" / "adversarial"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "adversarial_corpus_summary.json"
    
    summary_data = {
        "total_vectors": len(results),
        "defended_count": len([r for r in results if r.defended]),
        "breached_count": len(failed),
        "crashed_count": len(crashed),
        "zero_500_guarantee": len(crashed) == 0,
        "defense_success_rate": f"{100.0 * (len(results) - len(failed)) / max(1, len(results)):.1f}%",
        "vectors": [r.to_dict() for r in results],
    }

    out_path.write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")
    print(f"Artifact successfully generated: {out_path}")

    # Also mirror into benchmarks directory
    bench_dir = REPO_ROOT / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "adversarial_corpus.json").write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")

    if failed or crashed:
        print(f"CRITICAL: {len(failed)} attack vectors breached defense, {len(crashed)} caused HTTP 500!")
        return 1

    print(f"SUCCESS: All {len(results)} attack vectors safely defended with 0 crashes (Zero HTTP 500s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
