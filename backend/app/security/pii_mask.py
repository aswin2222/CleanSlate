"""PII Masking module to prevent data leakage in LLM prompts."""
from __future__ import annotations

import re
from typing import List, Sequence

# Regex patterns for common PII
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
LONG_DIGIT_REGEX = re.compile(r"\b\d{7,}\b")
IP_ADDR_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def mask_pii_value(value: str) -> str:
    """
    Replaces PII patterns (emails, phone numbers, SSNs, credit cards, long digits)
    with semantic placeholder tokens.
    """
    if not value or not isinstance(value, str):
        return str(value) if value is not None else ""

    masked = value
    masked = EMAIL_REGEX.sub("[EMAIL]", masked)
    masked = SSN_REGEX.sub("[SSN]", masked)
    masked = CREDIT_CARD_REGEX.sub("[CARD_NUM]", masked)
    masked = PHONE_REGEX.sub("[PHONE]", masked)
    masked = LONG_DIGIT_REGEX.sub("[DIGITS]", masked)
    masked = IP_ADDR_REGEX.sub("[IP]", masked)
    return masked


def mask_sample_values(values: Sequence[str], max_samples: int = 5) -> List[str]:
    """
    Selects up to max_samples distinct non-empty values and returns PII-masked representations.
    """
    samples: List[str] = []
    seen = set()

    for val in values:
        if val is None:
            continue
        s_val = str(val).strip()
        if not s_val or s_val.lower() in ("nan", "null", "none", ""):
            continue
        masked = mask_pii_value(s_val)
        if masked not in seen:
            seen.add(masked)
            samples.append(masked)
            if len(samples) >= max_samples:
                break

    return samples
