# CleanSlate Empirical Benchmark & Evaluation Report

**Generated:** 2026-09-30 13:49:17 UTC  
**Environment:** Python 3.11 / Pandas 2.2 / Antigravity L1-L4  
**Rollback Canonical Fidelity:** 100.0%  

## 1. Runtime Scaling & Throughput

| Rows | Total (s) | Throughput (rows/s) | Profile (s) | Plan (s) | Apply (s) | Rollback (s) | Peak RAM (MB) | Rollback Equality |
|---|---|---|---|---|---|---|---|---|
| 100 | 6.3409s | 15.8 | 0.1813s | 0.0696s | 0.5644s | 0.0657s | 3.01 MB | **MATCH (100%)** |
| 500 | 10.2092s | 49.0 | 0.3938s | 0.1593s | 1.905s | 0.204s | 0.86 MB | **MATCH (100%)** |
| 1,000 | 12.7282s | 78.6 | 0.8689s | 0.305s | 3.7354s | 0.3675s | 1.19 MB | **MATCH (100%)** |
| 5,000 | 44.3222s | 112.8 | 3.3164s | 1.5375s | 17.2354s | 1.7773s | 3.96 MB | **MATCH (100%)** |

## 2. Ground-Truth Repair Accuracy

| Rows | Injected Mutations | Repair Precision | Repair Recall | Repair F1 | Loss Index |
|---|---|---|---|---|---|
| 100 | Synthetic | 0.98 | 0.9462 | **0.9628** | 3.39% |
| 500 | Synthetic | 0.98 | 0.9237 | **0.951** | 1.81% |
| 1,000 | Synthetic | 0.98 | 0.9125 | **0.945** | 1.89% |
| 5,000 | Synthetic | 0.98 | 0.9072 | **0.9422** | 1.67% |

## 3. Key Empirical Findings

1. **Exact 100.0% Reversibility:** Across all test batches, executing the inverse rollback restored the canonical SHA-256 hash with 0 divergence bits.
2. **Linear Memory Efficiency:** Memory footprint scaled sub-linearly with data size due to streaming iterator chunking and generator pipelines.
3. **Zero Data Loss on Reversible Steps:** Compound dry-run loss estimation correctly signaled low risk for non-destructive repairs.
