"""Unit tests for multiformat clean dataset exporter (auto/input format, CSV, TSV, XLSX, JSON, Parquet)."""
from __future__ import annotations

import io
import json
import pandas as pd
import pytest

from app.export.exporter import (
    build_export_filename,
    export_dataframe_to_response,
    resolve_export_format,
    sanitize_dataframe_for_export,
)


def test_resolve_export_format():
    # When auto, matches detected format or file extension
    assert resolve_export_format("xlsx", "data.xlsx", "auto") == "xlsx"
    assert resolve_export_format("tsv", "records.tsv", "auto") == "tsv"
    assert resolve_export_format("json", "feed.json", "auto") == "json"
    assert resolve_export_format("jsonl", "events.ndjson", "auto") == "jsonl"
    assert resolve_export_format("parquet", "lake.parquet", "auto") == "parquet"
    assert resolve_export_format("csv", "users.csv", "auto") == "csv"

    # When explicit format is requested, honors explicit format
    assert resolve_export_format("csv", "users.csv", "xlsx") == "xlsx"
    assert resolve_export_format("xlsx", "data.xlsx", "json") == "json"
    assert resolve_export_format("csv", "users.csv", "parquet") == "parquet"


def test_build_export_filename():
    assert build_export_filename("dirty_sales.xlsx", "xlsx") == "cleaned_dirty_sales.xlsx"
    assert build_export_filename("dirty_sales.csv", "parquet") == "cleaned_dirty_sales.parquet"
    assert build_export_filename("cleaned_users.csv", "csv") == "cleaned_users.csv"
    assert build_export_filename("clean_users.csv", "csv") == "cleaned_users.csv"


def test_sanitize_dataframe_for_export():
    df = pd.DataFrame({
        "name": ["Alice", "=cmd|'calc'!A0", "+malicious", "-negative", "@mention", "Normal"],
        "age": ["25", "30", "35", "40", "45", "50"],
    })
    safe_df = sanitize_dataframe_for_export(df)
    # Triggers starting with =, +, -, @ must be prepended with a single quote
    assert safe_df["name"].iloc[0] == "Alice"
    assert safe_df["name"].iloc[1].startswith("'=")
    assert safe_df["name"].iloc[2].startswith("'+")
    assert safe_df["name"].iloc[3].startswith("'-")
    assert safe_df["name"].iloc[4].startswith("'@")
    assert safe_df["name"].iloc[5] == "Normal"


def test_export_auto_same_as_input_csv():
    df = pd.DataFrame({
        "_rid": [0, 1],
        "name": ["Alice", "Bob"],
        "email": ["alice@corp.com", "bob@corp.com"],
    })
    resp = export_dataframe_to_response(
        df=df,
        original_filename="raw_users.csv",
        detected_format="csv",
        requested_format="auto",
    )
    assert resp.media_type == "text/csv; charset=utf-8"
    assert 'filename="cleaned_raw_users.csv"' in resp.headers["Content-Disposition"]
    content = resp.body.decode("utf-8")
    assert "_rid" not in content
    assert "Alice" in content
    assert "bob@corp.com" in content


def test_export_auto_same_as_input_xlsx():
    df = pd.DataFrame({
        "_rid": [0, 1],
        "product": ["Widget", "Gadget"],
        "price": ["19.99", "29.99"],
    })
    resp = export_dataframe_to_response(
        df=df,
        original_filename="products.xlsx",
        detected_format="xlsx",
        requested_format="auto",
    )
    assert "spreadsheetml" in resp.media_type
    assert 'filename="cleaned_products.xlsx"' in resp.headers["Content-Disposition"]

    # Verify content can be read back with openpyxl / pandas
    loaded_df = pd.read_excel(io.BytesIO(resp.body), engine="openpyxl")
    assert "_rid" not in loaded_df.columns
    assert "product" in loaded_df.columns
    assert len(loaded_df) == 2


def test_export_auto_same_as_input_tsv():
    df = pd.DataFrame({
        "_rid": [0],
        "colA": ["Val1"],
        "colB": ["Val2"],
    })
    resp = export_dataframe_to_response(
        df=df,
        original_filename="tab_data.tsv",
        detected_format="tsv",
        requested_format="auto",
    )
    assert "tab-separated-values" in resp.media_type
    assert 'filename="cleaned_tab_data.tsv"' in resp.headers["Content-Disposition"]
    content = resp.body.decode("utf-8")
    assert "\t" in content
    assert "_rid" not in content


def test_export_json_and_jsonl():
    df = pd.DataFrame({
        "_rid": [0, 1],
        "city": ["New York", "London"],
    })
    # JSON
    resp_json = export_dataframe_to_response(
        df=df,
        original_filename="cities.json",
        detected_format="json",
        requested_format="auto",
    )
    data = json.loads(resp_json.body.decode("utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    assert "_rid" not in data[0]

    # JSONL
    resp_jsonl = export_dataframe_to_response(
        df=df,
        original_filename="cities.jsonl",
        detected_format="jsonl",
        requested_format="auto",
    )
    lines = resp_jsonl.body.decode("utf-8").strip().splitlines()
    assert len(lines) == 2
    row0 = json.loads(lines[0])
    assert row0["city"] == "New York"
    assert "_rid" not in row0


def test_export_parquet():
    df = pd.DataFrame({
        "_rid": [0, 1],
        "metric": [10.5, 20.2],
    })
    resp = export_dataframe_to_response(
        df=df,
        original_filename="metrics.parquet",
        detected_format="parquet",
        requested_format="auto",
    )
    assert 'filename="cleaned_metrics.parquet"' in resp.headers["Content-Disposition"]
    loaded = pd.read_parquet(io.BytesIO(resp.body))
    assert "_rid" not in loaded.columns
    assert len(loaded) == 2
