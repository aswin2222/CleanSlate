"""Encoding detection and byte normalization module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import charset_normalizer


@dataclass
class EncodingReport:
    detected_encoding: str
    confidence: float
    undecodable_byte_count: int
    has_bom: bool


def detect_and_decode(raw_bytes: bytes) -> Tuple[str, EncodingReport]:
    """
    Detects character encoding (UTF-8, UTF-16, Latin-1, etc.), resolves BOMs,
    and replaces undecodable bytes with Unicode replacement character U+FFFD.
    Returns (decoded_text, EncodingReport).
    """
    has_bom = False
    detected_encoding = "utf-8"
    confidence = 1.0

    # 1. BOM detection
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        has_bom = True
        detected_encoding = "utf-8-sig"
        decoded = raw_bytes[3:].decode("utf-8", errors="replace")
        return decoded, EncodingReport(detected_encoding, 1.0, decoded.count("\ufffd"), has_bom)
    elif raw_bytes.startswith(b"\xff\xfe\x00\x00"):
        has_bom = True
        detected_encoding = "utf-32-le"
        decoded = raw_bytes.decode(detected_encoding, errors="replace")
        return decoded, EncodingReport(detected_encoding, 1.0, decoded.count("\ufffd"), has_bom)
    elif raw_bytes.startswith(b"\x00\x00\xfe\xff"):
        has_bom = True
        detected_encoding = "utf-32-be"
        decoded = raw_bytes.decode(detected_encoding, errors="replace")
        return decoded, EncodingReport(detected_encoding, 1.0, decoded.count("\ufffd"), has_bom)
    elif raw_bytes.startswith(b"\xff\xfe"):
        has_bom = True
        detected_encoding = "utf-16-le"
        decoded = raw_bytes.decode(detected_encoding, errors="replace")
        return decoded, EncodingReport(detected_encoding, 1.0, decoded.count("\ufffd"), has_bom)
    elif raw_bytes.startswith(b"\xfe\xff"):
        has_bom = True
        detected_encoding = "utf-16-be"
        decoded = raw_bytes.decode(detected_encoding, errors="replace")
        return decoded, EncodingReport(detected_encoding, 1.0, decoded.count("\ufffd"), has_bom)

    # 2. Try clean strict UTF-8
    try:
        decoded_strict = raw_bytes.decode("utf-8")
        return decoded_strict, EncodingReport("utf-8", 1.0, 0, False)
    except UnicodeDecodeError:
        pass

    # 3. Statistical detection
    best = None
    try:
        matches = charset_normalizer.from_bytes(raw_bytes)
        best = matches.best()
    except Exception:
        pass

    if best is not None and best.encoding.lower() not in ("cp1006", "cp850", "mac_roman", "mac_arabic"):
        detected_encoding = best.encoding
        chaos = getattr(best, "chaos", 0.1)
        confidence = float(max(0.0, min(1.0, 1.0 - (chaos if chaos is not None else 0.1))))
    else:
        # Default to utf-8 with replacement
        detected_encoding = "utf-8"
        confidence = 0.7

    try:
        decoded_text = raw_bytes.decode(detected_encoding, errors="replace")
    except Exception:
        decoded_text = raw_bytes.decode("utf-8", errors="replace")

    replacement_count = decoded_text.count("\ufffd")

    return decoded_text, EncodingReport(
        detected_encoding=detected_encoding,
        confidence=confidence,
        undecodable_byte_count=replacement_count,
        has_bom=has_bom,
    )
