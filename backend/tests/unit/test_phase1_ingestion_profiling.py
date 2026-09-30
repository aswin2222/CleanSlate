"""Unit tests for Phase 1: Ingestion, Upload Guard, Quarantine, Profiling, and Sparsity."""
from __future__ import annotations

import io
import json
import zipfile
import pytest
import pandas as pd
import numpy as np

from app.security.upload_guard import UploadGuard, GuardErrorCode
from app.security.sanitize import sanitize_filename, is_formula_injection, neutralize_for_export
from app.security.pii_mask import mask_pii_value, mask_sample_values
from app.ingestion.encoding import detect_and_decode
from app.ingestion.rowid import assign_stable_row_ids, deduplicate_headers
from app.ingestion.readers import read_dataset_file, sniff_delimiter, read_csv_or_tsv, read_json_or_ndjson
from app.profiling.patterns import is_missing, infer_value_type, generate_pattern_signature
from app.profiling.sparsity import evaluate_sparsity
from app.profiling.profiler import profile_dataset, profile_column


class TestUploadGuardAndSanitization:
    def test_empty_file_rejected(self):
        guard = UploadGuard()
        report = guard.inspect_file(b"", "empty.csv")
        assert not report.is_valid
        assert report.error_code == GuardErrorCode.EMPTY_FILE

    def test_file_too_large(self):
        guard = UploadGuard(max_bytes=100)
        report = guard.inspect_file(b"x" * 150, "large.csv")
        assert not report.is_valid
        assert report.error_code == GuardErrorCode.FILE_TOO_LARGE

    def test_invalid_extension(self):
        guard = UploadGuard()
        report = guard.inspect_file(b"content", "dangerous.exe")
        assert not report.is_valid
        assert report.error_code == GuardErrorCode.INVALID_EXTENSION

    def test_magic_mismatch_parquet(self):
        guard = UploadGuard()
        report = guard.inspect_file(b"NOT_A_PARQUET_FILE", "test.parquet")
        assert not report.is_valid
        assert report.error_code == GuardErrorCode.MAGIC_MISMATCH

    def test_zip_bomb_detection(self):
        # Create a compressed zip payload that exceeds expansion ratio
        guard = UploadGuard(zip_expansion_ratio=5, zip_max_uncompressed=1000000)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 100,000 zeros compresses to very few bytes (> 100:1 ratio)
            zf.writestr("huge.txt", b"0" * 100000)
        zip_bytes = buffer.getvalue()
        report = guard.inspect_file(zip_bytes, "test.xlsx")
        assert not report.is_valid
        assert report.error_code == GuardErrorCode.ZIP_BOMB_DETECTED

    def test_sanitize_filename_traversal(self):
        safe_name, key = sanitize_filename("../../etc/passwd")
        assert "/" not in safe_name
        assert ".." not in safe_name
        assert key.endswith(safe_name)

    def test_formula_injection_detection_and_neutralization(self):
        assert is_formula_injection("=cmd|'/C calc'!A0")
        assert is_formula_injection("+12345")
        assert is_formula_injection("-SUM(A1:A10)")
        assert is_formula_injection("@HYPERLINK('http://evil.com')")
        assert not is_formula_injection("Standard Customer Name")

        neutralized = neutralize_for_export("=cmd|'/C calc'!A0")
        assert neutralized == "'=cmd|'/C calc'!A0"
        assert neutralize_for_export("Normal Text") == "Normal Text"

    def test_pii_masking(self):
        masked_email = mask_pii_value("contact john.doe@example.com for support")
        assert "[EMAIL]" in masked_email
        assert "john.doe@example.com" not in masked_email

        masked_phone = mask_pii_value("call +1-555-123-4567 immediately")
        assert "[PHONE]" in masked_phone

        samples = mask_sample_values(["alice@test.com", "bob@corp.org", "normal_value", "alice@test.com"])
        assert len(samples) == 2
        assert samples[0] == "[EMAIL]"
        assert samples[1] == "normal_value"


class TestEncodingAndRowId:
    def test_encoding_bom_detection(self):
        utf8_bom = b"\xef\xbb\xbfname,age\nAlice,30"
        text, report = detect_and_decode(utf8_bom)
        assert report.has_bom
        assert "Alice" in text

    def test_undecodable_byte_replacement(self):
        # Invalid UTF-8 sequence
        bad_bytes = b"header\nvalid_text_\xff\xfe_invalid"
        text, report = detect_and_decode(bad_bytes)
        assert report.undecodable_byte_count > 0 or "\ufffd" in text

    def test_deduplicate_headers(self):
        raw = ["id", "amount", "id", "amount", "id"]
        deduped, mapping = deduplicate_headers(raw)
        assert deduped == ["id", "amount", "id_2", "amount_2", "id_3"]
        assert len(mapping["id"]) == 3

    def test_assign_stable_row_ids(self):
        df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": ["1", "2", "3"]})
        df_with_rid = assign_stable_row_ids(df)
        assert "_rid" in df_with_rid.columns
        assert list(df_with_rid["_rid"]) == [0, 1, 2]
        assert df_with_rid.columns[0] == "_rid"


class TestIngestionAndQuarantine:
    def test_csv_ingestion_preserves_strings(self):
        csv_data = "code,phone,large_id\n007,+919876543210,123456789012345678901234567890\n"
        res = read_dataset_file(csv_data.encode("utf-8"), "customers.csv")
        assert res.valid_rows == 1
        assert res.df["code"].iloc[0] == "007"
        assert res.df["phone"].iloc[0] == "+919876543210"
        assert res.df["large_id"].iloc[0] == "123456789012345678901234567890"

    def test_ragged_rows_sent_to_quarantine(self):
        csv_data = "colA,colB,colC\nval1,val2,val3\nragged1,ragged2\nvalid4,valid5,valid6\nragged_too_many,a,b,c,d\n"
        res = read_dataset_file(csv_data.encode("utf-8"), "ragged.csv")
        assert res.valid_rows == 2
        assert len(res.quarantine) == 2
        assert res.quarantine[0].line_no == 3
        assert "Ragged column count" in res.quarantine[0].reason

    def test_delimiter_sniffing(self):
        tsv_data = "id\tname\tage\n1\tAlice\t25\n2\tBob\t30\n"
        assert sniff_delimiter(tsv_data) == "\t"
        res = read_dataset_file(tsv_data.encode("utf-8"), "data.tsv")
        assert res.valid_rows == 2
        assert "name" in res.df.columns

    def test_json_and_ndjson_ingestion_with_flattening(self):
        # NDJSON with 1-level nested object
        ndjson = (
            '{"id": "1", "user": {"name": "Alice", "city": "NY"}, "status": "active"}\n'
            '{"id": "2", "user": {"name": "Bob", "city": "SF"}, "status": "pending"}\n'
        )
        res = read_dataset_file(ndjson.encode("utf-8"), "users.jsonl")
        assert res.valid_rows == 2
        assert "user_name" in res.df.columns
        assert "user_city" in res.df.columns
        assert res.df["user_name"].iloc[0] == "Alice"


class TestProfilingAndSparsity:
    def test_missing_markers_identification(self):
        for marker in ["", " ", "N/A", "NA", "null", "NULL", "None", "nan", "-", "--", "?", "unknown", "n/a", "#N/A"]:
            assert is_missing(marker), f"Failed to identify {marker} as missing"
        assert not is_missing("Valid Value")

    def test_semantic_neutral_type_inference(self):
        assert infer_value_type("12345") == "int"
        assert infer_value_type("-42.50") == "float"
        assert infer_value_type("test@domain.com") == "email"
        assert infer_value_type("2024-03-15") == "date"
        assert infer_value_type("+1 800 555 1234") == "phone"
        assert infer_value_type("true") == "bool"
        assert infer_value_type("$1,249.99") == "currency"
        assert infer_value_type("A random free text description") == "text"

    def test_pattern_signatures(self):
        assert generate_pattern_signature("2024-05-12") == "9999-99-99"
        assert generate_pattern_signature("John Doe") == "Aaaa Aaa"

    def test_sparsity_and_low_evidence_flags(self):
        # 10 rows: less than MIN_ROWS_FOR_INFERENCE (30) -> low evidence
        small_df = pd.DataFrame({
            "col_normal": [f"val_{i}" for i in range(10)],
            "col_sparse": ["v"] + [""] * 9,  # 90% null -> extreme sparse
        })
        rep = evaluate_sparsity(small_df, sparse_threshold=0.90, min_rows=30)
        assert rep.is_low_evidence
        assert "col_sparse" in rep.extreme_sparse_columns
        assert rep.column_reports["col_sparse"].is_extreme_sparse

    def test_profile_dataset_comprehensive(self):
        df = pd.DataFrame({
            "_rid": list(range(50)),
            "age": ["25", "30", "35", "40", "150", "N/A"] + ["30"] * 44,  # Outlier 150
            "date": ["2024-01-01", "01/02/2024", "01-03-2024"] + ["2024-01-01"] * 47,  # Multiple formats
            "notes": ["  dirty ws  ", "clean", "clean", "clean"] + ["clean"] * 46,
        })
        profile = profile_dataset(df)
        assert profile.total_rows == 50
        assert "age" in profile.columns
        assert profile.columns["age"].is_numeric
        assert profile.columns["age"].iqr_outliers_count >= 1
        assert profile.columns["date"].format_variants
        assert profile.columns["notes"].leading_trailing_whitespace_count >= 1
        assert profile.fingerprint != ""
        d = profile.to_dict()
        assert isinstance(d, dict)
        json_str = json.dumps(d)
        assert len(json_str) > 0
