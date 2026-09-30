"""Prometheus metrics exporter and instrumentation counters."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "cleanslate_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
    "cleanslate_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

# Pipeline stage latency
STAGE_LATENCY = Histogram(
    "cleanslate_stage_latency_seconds",
    "Processing time for individual pipeline stages",
    ["stage"],
)

# Upload & Security counters
UPLOAD_GUARD_REJECTIONS = Counter(
    "cleanslate_upload_guard_rejections_total",
    "Total files rejected by upload guard",
    ["error_code"],
)
QUARANTINED_ROWS_TOTAL = Counter(
    "cleanslate_quarantined_rows_total",
    "Total ragged or malformed lines routed to quarantine",
)

# LLM metrics
LLM_CALLS_TOTAL = Counter("cleanslate_llm_calls_total", "Total requests sent to LLM")
LLM_FAILURES_TOTAL = Counter("cleanslate_llm_failures_total", "Total LLM failures / timeouts")
LLM_LATENCY = Histogram("cleanslate_llm_latency_seconds", "LLM request latency in seconds")

# Execution & Reversibility Safety
APPLIES_TOTAL = Counter("cleanslate_applies_total", "Total transformation steps executed")
ROLLBACKS_TOTAL = Counter("cleanslate_rollbacks_total", "Total rollback executions")
ROLLBACK_HASH_MISMATCHES = Counter(
    "cleanslate_rollback_hash_mismatches_total",
    "Total rollback state mismatches (Target MUST BE 0)",
)

# Verification & Mutation
TESTS_PASSED_TOTAL = Counter("cleanslate_tests_passed_total", "Total validation tests passed")
TESTS_FAILED_TOTAL = Counter("cleanslate_tests_failed_total", "Total validation tests failed")
MUTATION_DETECTION_RATE = Gauge(
    "cleanslate_mutation_detection_rate",
    "Current suite mutation fault detection percentage",
)
ADVERSARIAL_SURVIVAL_RATE = Gauge(
    "cleanslate_adversarial_survival_rate",
    "Adversarial corpus survival percentage (Target 100%)",
)
