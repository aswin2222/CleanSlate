"""Script to run CleanSlate benchmarks across 100, 500, 1000, and 5000 rows and write results."""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.evaluation.benchmark import BenchmarkSuite


def main():
    bench = BenchmarkSuite(output_dir="benchmarks")
    print("Running CleanSlate empirical scaling benchmark...")
    results = bench.run_scaling_benchmark(row_counts=[100, 500, 1000, 5000])
    print(f"Benchmark complete! Output written to benchmarks/results.json and benchmarks/report.md")
    for r in results["scaling_benchmark"]:
        print(f"Rows: {r['n_rows']:>5} | Total: {r['total_sec']}s | Throughput: {r['throughput_rows_sec']:>7.1f} rows/s | RAM: {r['peak_memory_mb']:>5.2f} MB | Rollback: {r['rollback_match']}")


if __name__ == "__main__":
    main()
