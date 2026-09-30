"""Data sanitization, filename security, and CSV formula injection neutralization."""
from __future__ import annotations

import html
import re
import uuid
from typing import Any, Tuple

# CSV formula injection trigger characters (including leading tab and CR)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_filename(filename: str) -> Tuple[str, str]:
    """
    Sanitizes user-provided filename, preventing path traversal attacks.
    Returns:
        (safe_display_name, storage_uuid_key)
    """
    # Remove directory separators and path traversal
    clean_name = re.sub(r"\.\.+", "", filename)
    clean_name = re.sub(r"[\\/]+", "_", clean_name).strip()
    clean_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean_name)
    clean_name = clean_name.lstrip("._")

    # Default fallback
    if not clean_name or clean_name in (".", ".."):
        clean_name = "unnamed_dataset"

    # Truncate if excessively long
    if len(clean_name) > 200:
        clean_name = clean_name[:200]

    unique_key = f"{uuid.uuid4().hex}_{clean_name}"
    return clean_name, unique_key


def is_formula_injection(value: str) -> bool:
    """
    Checks if a string begins with a formula trigger character.
    Untrusted formula execution occurs in Excel/Calc if starting with =, +, -, @, \t, \r.
    """
    if not value or not isinstance(value, str):
        return False
    stripped = value.lstrip()
    return stripped.startswith(FORMULA_PREFIXES)


def neutralize_for_export(value: Any) -> str:
    """
    Neutralizes formula injection for CSV export by prefixing with a single quote (').
    Preserves exact value if not an injection trigger.
    """
    if value is None:
        return ""
    str_val = str(value)
    if is_formula_injection(str_val):
        return "'" + str_val
    return str_val


def escape_cell_text(value: Any) -> str:
    """
    Escapes text for safe plain HTML/UI rendering.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)
