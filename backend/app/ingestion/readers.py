"""Enterprise multiformat ingestion readers with robust delimiter sniffing and quarantine."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from app.config import settings
from app.ingestion.encoding import detect_and_decode, EncodingReport
from app.ingestion.rowid import ROW_ID_COL, assign_stable_row_ids, deduplicate_headers
from app.security.sanitize import is_formula_injection


@dataclass
class QuarantineRecord:
    line_no: int
    raw_text: str
    reason: str


@dataclass
class IngestionResult:
    df: pd.DataFrame
    quarantine: List[QuarantineRecord]
    header_mapping: Dict[str, List[str]]
    detected_format: str
    encoding_report: EncodingReport
    total_raw_rows: int
    valid_rows: int
    formula_injection_count: int
    original_columns: List[str]


def sniff_delimiter(sample_text: str) -> str:
    """Sniffs the most probable CSV/TSV delimiter from header/data sample."""
    candidates = [",", "\t", ";", "|"]
    first_few_lines = "\n".join(sample_text.splitlines()[:10])
    if not first_few_lines.strip():
        return ","

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(first_few_lines, delimiters=",\t;|")
        if dialect.delimiter in candidates:
            return dialect.delimiter
    except Exception:
        pass

    # Fallback frequency count across lines
    lines = [line for line in first_few_lines.splitlines() if line.strip()]
    if not lines:
        return ","

    best_delim = ","
    best_score = -1
    for delim in candidates:
        counts = [line.count(delim) for line in lines]
        # Prefer delims that appear consistently > 0 times per line
        if counts and all(c > 0 for c in counts) and len(set(counts)) == 1:
            return delim
        avg = sum(counts) / len(counts) if counts else 0
        if avg > best_score:
            best_score = avg
            best_delim = delim

    return best_delim


def read_csv_or_tsv(
    content_str: str,
    delimiter: Optional[str] = None,
    max_field_len: int = settings.MAX_FIELD_LENGTH,
) -> Tuple[pd.DataFrame, List[QuarantineRecord], Dict[str, List[str]], int]:
    """
    Parses CSV/TSV data as raw strings, isolating malformed/ragged rows to quarantine.
    """
    if not delimiter:
        delimiter = sniff_delimiter(content_str[:10000])

    lines = content_str.splitlines()
    if not lines:
        return pd.DataFrame(), [], {}, 0

    reader = csv.reader(io.StringIO(content_str), delimiter=delimiter)
    try:
        raw_header = next(reader)
    except StopIteration:
        return pd.DataFrame(), [], {}, 0
    except Exception as e:
        return pd.DataFrame(), [QuarantineRecord(line_no=1, raw_text=lines[0] if lines else "", reason=f"Header read error: {str(e)}")], {}, 0

    expected_cols = len(raw_header)
    clean_headers, header_mapping = deduplicate_headers(raw_header)

    valid_rows: List[List[str]] = []
    quarantine: List[QuarantineRecord] = []
    formula_count = 0

    # Parse rows one by one to never crash on ragged/malformed lines
    line_no = 1  # 1 was header
    for line_text in lines[1:]:
        line_no += 1
        if not line_text.strip():
            continue  # empty line ignored
        try:
            row_parsed = list(csv.reader([line_text], delimiter=delimiter))[0]
            if len(row_parsed) != expected_cols:
                quarantine.append(
                    QuarantineRecord(
                        line_no=line_no,
                        raw_text=line_text[:1000],
                        reason=f"Ragged column count: expected {expected_cols}, got {len(row_parsed)}",
                    )
                )
                continue

            # Check field length and formula injection
            sanitized_row: List[str] = []
            for cell in row_parsed:
                c_str = str(cell)
                if is_formula_injection(c_str):
                    formula_count += 1
                if len(c_str) > max_field_len:
                    # Truncate working view copy per spec
                    c_str = c_str[:max_field_len]
                sanitized_row.append(c_str)

            valid_rows.append(sanitized_row)
        except Exception as err:
            quarantine.append(
                QuarantineRecord(
                    line_no=line_no,
                    raw_text=line_text[:1000],
                    reason=f"Malformed line parse error: {str(err)}",
                )
            )

    df = pd.DataFrame(valid_rows, columns=clean_headers, dtype=str)
    return df, quarantine, header_mapping, formula_count


def read_json_or_ndjson(
    content_str: str,
    max_field_len: int = settings.MAX_FIELD_LENGTH,
) -> Tuple[pd.DataFrame, List[QuarantineRecord], Dict[str, List[str]], int]:
    """
    Parses standard JSON array of objects or newline-delimited JSON (JSONL/NDJSON),
    flattening one nesting level and loading all values as strings.
    """
    quarantine: List[QuarantineRecord] = []
    parsed_records: List[Dict[str, Any]] = []
    formula_count = 0

    stripped = content_str.strip()
    if stripped.startswith("["):
        # JSON array
        try:
            data = json.loads(content_str)
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        parsed_records.append(item)
                    else:
                        quarantine.append(
                            QuarantineRecord(
                                line_no=idx + 1,
                                raw_text=str(item)[:1000],
                                reason="JSON array element is not an object",
                            )
                        )
            else:
                quarantine.append(
                    QuarantineRecord(
                        line_no=1,
                        raw_text=content_str[:500],
                        reason="Top-level JSON is not an array of objects",
                    )
                )
        except Exception as e:
            quarantine.append(
                QuarantineRecord(
                    line_no=1,
                    raw_text=content_str[:500],
                    reason=f"JSON parse error: {str(e)}",
                )
            )
    else:
        # JSONL / NDJSON
        for line_no, line in enumerate(content_str.splitlines(), start=1):
            s_line = line.strip()
            if not s_line:
                continue
            try:
                obj = json.loads(s_line)
                if isinstance(obj, dict):
                    parsed_records.append(obj)
                else:
                    quarantine.append(
                        QuarantineRecord(
                            line_no=line_no,
                            raw_text=s_line[:1000],
                            reason="JSON line is not an object",
                        )
                    )
            except Exception as e:
                quarantine.append(
                    QuarantineRecord(
                        line_no=line_no,
                        raw_text=s_line[:1000],
                        reason=f"JSON line parse error: {str(e)}",
                    )
                )

    if not parsed_records:
        return pd.DataFrame(), quarantine, {}, 0

    # Flatten 1 nesting level
    flattened_rows: List[Dict[str, str]] = []
    all_keys: Dict[str, None] = {}

    for rec in parsed_records:
        flat_rec: Dict[str, str] = {}
        for k, v in rec.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    compound_key = f"{k}_{sub_k}"
                    all_keys[compound_key] = None
                    c_val = str(sub_v) if sub_v is not None else ""
                    if is_formula_injection(c_val):
                        formula_count += 1
                    flat_rec[compound_key] = c_val[:max_field_len]
            else:
                all_keys[k] = None
                c_val = str(v) if v is not None else ""
                if is_formula_injection(c_val):
                    formula_count += 1
                flat_rec[k] = c_val[:max_field_len]
        flattened_rows.append(flat_rec)

    headers = list(all_keys.keys())
    clean_headers, header_mapping = deduplicate_headers(headers)
    normalized_rows = []
    for r in flattened_rows:
        normalized_rows.append([r.get(k, "") for k in headers])

    df = pd.DataFrame(normalized_rows, columns=clean_headers, dtype=str)
    return df, quarantine, header_mapping, formula_count


def read_dataset_file(
    file_bytes: bytes,
    filename: str,
    sheet_name: Optional[Union[str, int]] = 0,
) -> IngestionResult:
    """
    Master ingestion router for enterprise files: CSV, TSV, JSON, JSONL, XLSX, Parquet.
    Guarantees:
    - Ingests all cells as strings (dtype=str, keep_default_na=False)
    - Automatically assigns stable _rid (0..n-1)
    - Records quarantine rows without terminating processing
    - Detects and neutralizes formulas on export
    """
    ext = Path(filename).suffix.lower()
    quarantine: List[QuarantineRecord] = []
    header_mapping: Dict[str, List[str]] = {}
    formula_count = 0
    df = pd.DataFrame()

    if ext in (".xlsx", ".xls"):
        # Excel parsing
        try:
            excel_df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=sheet_name if sheet_name is not None else 0,
                dtype=str,
                keep_default_na=False,
            )
            raw_cols = [str(c) for c in excel_df.columns]
            clean_headers, header_mapping = deduplicate_headers(raw_cols)
            excel_df.columns = pd.Index(clean_headers)
            # Count formula injection triggers
            for col in excel_df.columns:
                formula_count += int(excel_df[col].astype(str).apply(is_formula_injection).sum())
            df = excel_df.astype(str)
        except Exception as e:
            quarantine.append(QuarantineRecord(line_no=1, raw_text="XLSX binary stream", reason=f"Excel read error: {str(e)}"))
        encoding_report = EncodingReport("binary/zip", 1.0, 0, False)
        detected_format = "xlsx"

    elif ext == ".parquet":
        # Parquet parsing
        try:
            parquet_df = pd.read_parquet(io.BytesIO(file_bytes))
            raw_cols = [str(c) for c in parquet_df.columns]
            clean_headers, header_mapping = deduplicate_headers(raw_cols)
            parquet_df.columns = pd.Index(clean_headers)
            # Convert all to strings, replace NaNs with empty string
            df = parquet_df.fillna("").astype(str)
            for col in df.columns:
                formula_count += int(df[col].apply(is_formula_injection).sum())
        except Exception as e:
            quarantine.append(QuarantineRecord(line_no=1, raw_text="Parquet binary stream", reason=f"Parquet read error: {str(e)}"))
        encoding_report = EncodingReport("binary/parquet", 1.0, 0, False)
        detected_format = "parquet"

    elif ext in (".json", ".jsonl", ".ndjson"):
        text, encoding_report = detect_and_decode(file_bytes)
        df, quarantine, header_mapping, formula_count = read_json_or_ndjson(text)
        detected_format = "json" if ext == ".json" else "jsonl"

    else:
        # CSV / TSV / plain text fallback
        text, encoding_report = detect_and_decode(file_bytes)
        delimiter = "\t" if ext == ".tsv" else None
        df, quarantine, header_mapping, formula_count = read_csv_or_tsv(text, delimiter=delimiter)
        detected_format = "tsv" if ext == ".tsv" else "csv"

    # Always ensure dtype is str and missing is empty string
    if not df.empty:
        df = df.fillna("").astype(str)
        original_cols = [c for c in df.columns if c != ROW_ID_COL]
        # Assign stable row ID
        df = assign_stable_row_ids(df)
    else:
        original_cols = []

    return IngestionResult(
        df=df,
        quarantine=quarantine,
        header_mapping=header_mapping,
        detected_format=detected_format,
        encoding_report=encoding_report,
        total_raw_rows=len(df) + len(quarantine),
        valid_rows=len(df),
        formula_injection_count=formula_count,
        original_columns=original_cols,
    )
