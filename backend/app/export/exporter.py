"""Enterprise Dataset Exporter: Serializes clean datasets in original or converted formats."""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import Response

from app.security.sanitize import neutralize_for_export


def resolve_export_format(detected_format: str, original_filename: str, requested_format: str) -> str:
    """Resolves target export format, defaulting to the original input file format if 'auto'."""
    fmt = (requested_format or "auto").lower().strip()
    if fmt and fmt != "auto":
        return fmt

    norm_detected = (detected_format or "").lower().strip()
    if norm_detected in ("csv", "tsv", "xlsx", "xls", "json", "jsonl", "ndjson", "parquet"):
        if norm_detected in ("xlsx", "xls"):
            return "xlsx"
        if norm_detected == "ndjson":
            return "jsonl"
        return norm_detected

    ext = Path(original_filename or "").suffix.lower().lstrip(".")
    if ext in ("csv", "tsv", "xlsx", "xls", "json", "jsonl", "ndjson", "parquet"):
        if ext in ("xlsx", "xls"):
            return "xlsx"
        if ext == "ndjson":
            return "jsonl"
        return ext

    return "csv"


def build_export_filename(original_filename: str, target_format: str) -> str:
    """Generates clean output filename matching target extension."""
    raw_stem = Path(original_filename or "dataset").stem
    # Avoid repeating 'clean_' or 'cleaned_' prefix
    if raw_stem.lower().startswith("cleaned_"):
        clean_stem = raw_stem
    elif raw_stem.lower().startswith("clean_"):
        clean_stem = f"cleaned_{raw_stem[6:]}"
    else:
        clean_stem = f"cleaned_{raw_stem}"

    ext_map = {
        "csv": ".csv",
        "tsv": ".tsv",
        "xlsx": ".xlsx",
        "json": ".json",
        "jsonl": ".jsonl",
        "parquet": ".parquet",
        "ledger": "_ledger.json",
    }
    ext = ext_map.get(target_format, f".{target_format}")
    return f"{clean_stem}{ext}"


def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Neutralizes formula injection triggers in tabular string cells."""
    if hasattr(df, "map"):
        return df.map(neutralize_for_export)
    return df.applymap(neutralize_for_export)


def export_dataframe_to_response(
    df: pd.DataFrame,
    original_filename: str,
    detected_format: str,
    requested_format: str = "auto",
    ledger_entries: Optional[List[Any]] = None,
) -> Response:
    """
    Exports a clean DataFrame in the requested format (or matching input format).
    Guarantees:
    - Removes internal '_rid' column
    - Neutralizes spreadsheet formula injections for CSV/TSV/XLSX
    - Preserves UTF-8 encoding
    - Sets appropriate MIME media type and Content-Disposition attachment header
    """
    target_format = resolve_export_format(detected_format, original_filename, requested_format)
    export_filename = build_export_filename(original_filename, target_format)

    # Filter internal system columns
    export_cols = [c for c in df.columns if c != "_rid"]
    export_df = df[export_cols].copy().fillna("")

    if target_format == "csv":
        safe_df = sanitize_dataframe_for_export(export_df)
        csv_buf = io.StringIO()
        safe_df.to_csv(csv_buf, index=False)
        return Response(
            content=csv_buf.getvalue().encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "tsv":
        safe_df = sanitize_dataframe_for_export(export_df)
        tsv_buf = io.StringIO()
        safe_df.to_csv(tsv_buf, sep="\t", index=False)
        return Response(
            content=tsv_buf.getvalue().encode("utf-8"),
            media_type="text/tab-separated-values; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "xlsx":
        safe_df = sanitize_dataframe_for_export(export_df)
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            safe_df.to_excel(writer, index=False, sheet_name="CleanData")
        return Response(
            content=xlsx_buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "json":
        json_content = export_df.to_json(orient="records", indent=2, force_ascii=False)
        return Response(
            content=json_content.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "jsonl":
        jsonl_content = export_df.to_json(orient="records", lines=True, force_ascii=False)
        return Response(
            content=jsonl_content.encode("utf-8"),
            media_type="application/x-ndjson; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "parquet":
        pq_buf = io.BytesIO()
        export_df.to_parquet(pq_buf, index=False)
        return Response(
            content=pq_buf.getvalue(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    elif target_format == "ledger":
        ledger_data = []
        if ledger_entries:
            for e in ledger_entries:
                ledger_data.append({
                    "seq": getattr(e, "seq", None),
                    "step_id": getattr(e, "step_id", None),
                    "hash_before": getattr(e, "hash_before", None),
                    "hash_after": getattr(e, "hash_after", None),
                    "applied_at": getattr(e, "applied_at", "").isoformat() if hasattr(getattr(e, "applied_at", None), "isoformat") else str(getattr(e, "applied_at", "")),
                    "actor": getattr(e, "actor", None),
                    "reverted": getattr(e, "reverted", False),
                })
        return Response(
            content=json.dumps(ledger_data, indent=2).encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )

    else:
        # Default fallback to CSV
        safe_df = sanitize_dataframe_for_export(export_df)
        csv_buf = io.StringIO()
        safe_df.to_csv(csv_buf, index=False)
        return Response(
            content=csv_buf.getvalue().encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
        )
