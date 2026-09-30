"""Pattern detection, format signatures, and semantic-neutral type inference."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Comprehensive missing markers defined in Section 4.3:
# empty, N/A, NA, null, NULL, None, nan, -, --, ?, unknown, n/a, #N/A, whitespace-only
MISSING_MARKERS = {
    "",
    "n/a",
    "na",
    "null",
    "none",
    "nan",
    "-",
    "--",
    "?",
    "unknown",
    "#n/a",
}

# Regex pattern matchers for type candidates
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_PATTERN = re.compile(r"^(\+?\d{1,4}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}$")
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
IP_PATTERN = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
URL_PATTERN = re.compile(r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$")
CURRENCY_PATTERN = re.compile(
    r"^[\$€£¥₹]\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^[\$€£¥₹]\s*-?\d+(?:\.\d+)?$|^-?\d+(?:,\d{3})*(?:\.\d+)?\s*[\$€£¥₹]$"
)
PERCENTAGE_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?%$")

# Date pattern detectors
DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_US = re.compile(r"^\d{1,2}\/\d{1,2}\/\d{4}$")
DATE_EUR = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")
DATETIME_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$")


def is_missing(val: Optional[str]) -> bool:
    """Checks if a cell represents a missing/null value."""
    if val is None:
        return True
    s = str(val).strip()
    return s.lower() in MISSING_MARKERS


def generate_pattern_signature(val: str) -> str:
    """
    Transforms value into an abstract pattern signature:
    Digits -> 9, Uppercase -> A, Lowercase -> a, Special preserved.
    E.g., "2024-05-12" -> "9999-99-99", "John Doe" -> "Aaaa Aaa".
    """
    if not val:
        return ""
    sig = []
    for char in str(val)[:50]:
        if char.isdigit():
            sig.append("9")
        elif char.isupper():
            sig.append("A")
        elif char.islower():
            sig.append("a")
        else:
            sig.append(char)
    return "".join(sig)


def infer_value_type(val: str) -> str:
    """Infers the fine-grained semantic-neutral type of a single string value."""
    s = str(val).strip()
    if is_missing(s):
        return "null"

    # Boolean
    if s.lower() in ("true", "false", "t", "f", "yes", "no", "y", "n", "1", "0"):
        return "bool"

    # Currency (checked before int/float)
    if CURRENCY_PATTERN.match(s):
        return "currency"

    # Percentage
    if PERCENTAGE_PATTERN.match(s):
        return "percentage"

    # Integer
    if re.match(r"^-?\d+$", s):
        return "int"

    # Float
    if re.match(r"^-?\d+\.\d+$", s):
        return "float"

    # UUID
    if UUID_PATTERN.match(s):
        return "uuid"

    # Email
    if EMAIL_PATTERN.match(s):
        return "email"

    # IP
    if IP_PATTERN.match(s):
        return "ip"

    # URL
    if URL_PATTERN.match(s):
        return "url"

    # Date / Datetime
    if DATETIME_ISO.match(s):
        return "datetime"
    if DATE_ISO.match(s) or DATE_US.match(s) or DATE_EUR.match(s):
        return "date"

    # Phone
    if PHONE_PATTERN.match(s) and sum(c.isdigit() for c in s) in range(7, 16):
        return "phone"

    return "text"
