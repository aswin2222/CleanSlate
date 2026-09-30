"""Tests for synthetic corruptor and benchmark execution."""
import os
import pytest
import pandas as pd
from app.evaluation.corruptor import SyntheticCorruptor
from app.evaluation.benchmark import BenchmarkSuite, generate_benchmark_dataset


def test_synthetic_corruptor():
    clean_df = generate_benchmark_dataset(100)
    corruptor = SyntheticCorruptor(seed=123)
    dirty_df, mutations = corruptor.corrupt(clean_df)

    assert len(dirty_df) >= len(clean_df)
    assert len(mutations) > 0
    mutation_types = {m.mutation_type for m in mutations}
    assert "whitespace" in mutation_types or "outlier" in mutation_types or "case_inconsistency" in mutation_types


def test_benchmark_suite_execution(tmp_path):
    bench = BenchmarkSuite(output_dir=str(tmp_path))
    results = bench.run_scaling_benchmark(row_counts=[50, 100])

    assert "scaling_benchmark" in results
    assert len(results["scaling_benchmark"]) == 2
    for item in results["scaling_benchmark"]:
        assert item["rollback_match"] is True
        assert item["throughput_rows_sec"] > 0
        assert item["peak_memory_mb"] > 0

    assert os.path.exists(os.path.join(str(tmp_path), "results.json"))
    assert os.path.exists(os.path.join(str(tmp_path), "report.md"))
