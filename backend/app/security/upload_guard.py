"""Upload Guard and Ingestion Sanitization Engine."""
from __future__ import annotations

import io
import os
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.logging import logger
from app.security.sanitize import sanitize_filename, is_formula_injection


class GuardErrorCode(str, Enum):
    FILE_TOO_LARGE = "ERR_FILE_TOO_LARGE"
    INVALID_EXTENSION = "ERR_INVALID_EXTENSION"
    MAGIC_MISMATCH = "ERR_MAGIC_MISMATCH"
    ZIP_BOMB_DETECTED = "ERR_ZIP_BOMB_DETECTED"
    TOO_MANY_COLUMNS = "ERR_TOO_MANY_COLUMNS"
    ROW_LIMIT_EXCEEDED = "ERR_ROW_LIMIT_EXCEEDED"
    PARSE_TIMEOUT = "ERR_PARSE_TIMEOUT"
    PATH_TRAVERSAL = "ERR_PATH_TRAVERSAL"
    EMPTY_FILE = "ERR_EMPTY_FILE"
    MALFORMED_ARCHIVE = "ERR_MALFORMED_ARCHIVE"


@dataclass
class GuardReport:
    is_valid: bool
    error_code: Optional[GuardErrorCode] = None
    message: str = "Payload verified successfully"
    detected_format: str = "csv"
    sanitized_filename: str = ""
    storage_key: str = ""
    file_size_bytes: int = 0
    null_bytes_stripped: int = 0
    formula_injection_cells_detected: int = 0
    quarantine_count: int = 0
    details: Dict[str, str | int | float | bool] = field(default_factory=dict)


# Magic byte signatures
MAGIC_SIGNATURES: Dict[str, List[bytes]] = {
    "zip": [b"PK\x03\x04", b"PK\x05\x06"],  # xlsx is a zip
    "parquet": [b"PAR1"],
    "gzip": [b"\x1f\x8b"],
}

ALLOWED_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".xlsx", ".parquet", ".txt"}


class UploadGuard:
    def __init__(
        self,
        max_bytes: int = settings.MAX_UPLOAD_BYTES,
        max_columns: int = settings.MAX_COLUMNS,
        max_field_length: int = settings.MAX_FIELD_LENGTH,
        zip_expansion_ratio: int = settings.ZIP_MAX_EXPANSION_RATIO,
        zip_max_uncompressed: int = settings.ZIP_MAX_UNCOMPRESSED_BYTES,
    ):
        self.max_bytes = max_bytes
        self.max_columns = max_columns
        self.max_field_length = max_field_length
        self.zip_expansion_ratio = zip_expansion_ratio
        self.zip_max_uncompressed = zip_max_uncompressed

    def inspect_file(self, raw_bytes: bytes, filename: str) -> GuardReport:
        """Inspects raw payload against size, magic bytes, zip-bomb, and extension rules."""
        file_size = len(raw_bytes)
        safe_name, storage_key = sanitize_filename(filename)

        # 1. Check empty file
        if file_size == 0:
            return GuardReport(
                is_valid=False,
                error_code=GuardErrorCode.EMPTY_FILE,
                message="Uploaded file is empty (0 bytes)",
                sanitized_filename=safe_name,
                storage_key=storage_key,
                file_size_bytes=0,
            )

        # 2. Check maximum upload size
        if file_size > self.max_bytes:
            return GuardReport(
                is_valid=False,
                error_code=GuardErrorCode.FILE_TOO_LARGE,
                message=f"File size {file_size} exceeds maximum limit of {self.max_bytes} bytes",
                sanitized_filename=safe_name,
                storage_key=storage_key,
                file_size_bytes=file_size,
            )

        # 3. Check extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return GuardReport(
                is_valid=False,
                error_code=GuardErrorCode.INVALID_EXTENSION,
                message=f"Extension '{ext}' is not permitted. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}",
                sanitized_filename=safe_name,
                storage_key=storage_key,
                file_size_bytes=file_size,
            )

        # 4. Content sniffing / Magic bytes validation
        header_sample = raw_bytes[:16]
        detected_format = ext.lstrip(".")

        if ext == ".xlsx":
            if not any(header_sample.startswith(sig) for sig in MAGIC_SIGNATURES["zip"]):
                return GuardReport(
                    is_valid=False,
                    error_code=GuardErrorCode.MAGIC_MISMATCH,
                    message="File claimed to be XLSX but lacks ZIP container magic bytes",
                    sanitized_filename=safe_name,
                    storage_key=storage_key,
                    file_size_bytes=file_size,
                )
            # Verify zip bomb resistance
            zip_check = self._check_zip_bomb(raw_bytes)
            if not zip_check[0]:
                return GuardReport(
                    is_valid=False,
                    error_code=GuardErrorCode.ZIP_BOMB_DETECTED,
                    message=zip_check[1],
                    sanitized_filename=safe_name,
                    storage_key=storage_key,
                    file_size_bytes=file_size,
                )

        elif ext == ".parquet":
            if not header_sample.startswith(MAGIC_SIGNATURES["parquet"][0]):
                return GuardReport(
                    is_valid=False,
                    error_code=GuardErrorCode.MAGIC_MISMATCH,
                    message="File claimed to be Parquet but lacks 'PAR1' magic header",
                    sanitized_filename=safe_name,
                    storage_key=storage_key,
                    file_size_bytes=file_size,
                )

        # 5. Check and strip null bytes for text formats
        null_count = 0
        cleaned_bytes = raw_bytes
        if ext in (".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".txt"):
            null_count = raw_bytes.count(b"\x00")
            if null_count > 0:
                cleaned_bytes = raw_bytes.replace(b"\x00", b"")

        return GuardReport(
            is_valid=True,
            detected_format=detected_format,
            sanitized_filename=safe_name,
            storage_key=storage_key,
            file_size_bytes=file_size,
            null_bytes_stripped=null_count,
        )

    def _check_zip_bomb(self, raw_bytes: bytes) -> Tuple[bool, str]:
        """Validates that a zip/xlsx archive does not exceed expansion ratio or total limit."""
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                compressed_size = len(raw_bytes)

                if total_uncompressed > self.zip_max_uncompressed:
                    return (
                        False,
                        f"Uncompressed archive size {total_uncompressed}B exceeds limit of {self.zip_max_uncompressed}B",
                    )

                if compressed_size > 0:
                    ratio = total_uncompressed / compressed_size
                    if ratio > self.zip_expansion_ratio:
                        return (
                            False,
                            f"Compression ratio {ratio:.1f} exceeds safety threshold of {self.zip_expansion_ratio}:1",
                        )

                return True, "OK"
        except zipfile.BadZipFile:
            return False, "Malformed ZIP archive encountered"
        except Exception as e:
            return False, f"Archive inspection error: {str(e)}"
