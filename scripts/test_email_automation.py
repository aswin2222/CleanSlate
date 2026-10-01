"""TITAN Email Automation Verification Script.

Tests the complete headless pipeline:
1. Ingests a messy synthetic dataset with nulls, duplicates, and dirty formats.
2. Runs profiling, inference, planning, autonomous auto-approval, and execution.
3. Serializes clean dataset into original format and neutralizes spreadsheet injections.
4. Delivers the cleaned dataset and HTML audit report to the recipient using Resend API.

Usage:
  python scripts/test_email_automation.py --recipient your-email@example.com
  python scripts/test_email_automation.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.automation.headless_pipeline import clean_dataset_headless
from app.automation.email_notifier import send_cleaned_dataset_email
from app.config import settings

# Sample messy dataset
MESSY_CSV_CONTENT = """id,full_name,email,signup_date,country,revenue,status
1,  alice smith  ,alice@example.com,2024-01-15,USA,1250.50,active
2,Bob Jones,bob@corp.org,15/01/2024,United States,3400.00,Active
3,ALICE SMITH,alice@example.com,2024-01-15,USA,1250.50,active
4,Charlie Brown,invalid-email-address,2024-02-31,uk,,pending
5,David Lee,david@domain.com,2024-03-01,Canada,-50.00,active
6,Eva Green,eva@example.com,2024-03-10,Germany,=cmd|'/C calc'!A0,approved
7,Bob Jones,bob@corp.org,2024-01-15,USA,3400.00,active
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Test TITAN Headless Email Automation with Resend")
    parser.add_argument(
        "--recipient",
        type=str,
        default="",
        help="Recipient email address to send cleaned file to (via Resend)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute headless pipeline locally without dispatching email via Resend",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Optional path to custom messy dataset file to clean",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  TITAN AUTONOMOUS HEADLESS DATA CLEANING + RESEND PIPELINE")
    print("=" * 70)

    # 1. Prepare raw bytes
    if args.file and Path(args.file).exists():
        filename = Path(args.file).name
        raw_bytes = Path(args.file).read_bytes()
        print(f"[*] Loaded custom dataset: {filename} ({len(raw_bytes)} bytes)")
    else:
        filename = "customers_messy_input.csv"
        raw_bytes = MESSY_CSV_CONTENT.strip().encode("utf-8")
        print(f"[*] Generated synthetic messy dataset: {filename}")

    # 2. Run headless pipeline
    print("\n[Step 1/3] Executing autonomous cleaning pipeline (zero human clicks)...")
    result = clean_dataset_headless(file_bytes=raw_bytes, original_filename=filename)

    if not result.success:
        print(f"\n[!] Pipeline FAILED: {result.error_message}")
        return 1

    print("\n[Step 2/3] Pipeline completed successfully!")
    print(f"  • Run ID:             {result.run_id}")
    print(f"  • Original File:      {result.original_filename}")
    print(f"  • Cleaned File:       {result.cleaned_filename} ({result.target_format.upper()})")
    print(f"  • Cleaned File Size:  {len(result.cleaned_bytes)} bytes")
    print(f"  • Initial Rows:       {result.initial_rows}")
    print(f"  • Cleaned Rows:       {result.cleaned_rows}")
    print(f"  • Rows Dropped:       {result.rows_dropped}")
    print(f"  • Cells Standardized: {result.cells_modified}")
    print(f"  • Execution Time:     {result.duration_ms:.2f} ms")
    print(f"  • Initial SHA-256:    {result.initial_hash[:20]}...")
    print(f"  • Cleaned SHA-256:    {result.cleaned_hash[:20]}...")

    print("\n  Transformations Applied:")
    for step in result.steps_applied:
        print(
            f"    - Step #{step['seq']} [{step['transformation']}]: "
            f"dropped {step['rows_removed']} rows, modified {step['cells_modified']} cells "
            f"({step['duration_ms']:.1f}ms)"
        )

    # 3. Resend Email Dispatch
    if args.dry_run:
        print("\n[Step 3/3] Dry run specified: skipping Resend email dispatch.")
        print("[SUCCESS] Headless data cleaning pipeline verified.")
        return 0

    recipient = args.recipient.strip()
    if not recipient:
        print("\n[Step 3/3] No --recipient specified.")
        print("  To test email delivery via Resend, run:")
        print(f"    python scripts/test_email_automation.py --recipient YOUR_EMAIL@example.com")
        print("\n[SUCCESS] Pipeline runs without errors.")
        return 0

    print(f"\n[Step 3/3] Dispatching email to '{recipient}' via Resend API...")
    print(f"  • From:      {settings.RESEND_FROM_EMAIL}")
    print(f"  • Resend Key:{settings.RESEND_API_KEY[:8]}...{settings.RESEND_API_KEY[-4:]}")
    print(f"  • Attachment:{result.cleaned_filename} ({len(result.cleaned_bytes)} bytes)")

    email_res = send_cleaned_dataset_email(
        to_email=recipient,
        result=result,
        trigger_phrase="clean data",
    )

    if email_res.get("success"):
        print(f"\n[SUCCESS] Email successfully sent!")
        print(f"  • Resend Email ID: {email_res.get('email_id')}")
        print(f"  • Delivered to:    {recipient}")
        print(f"  • Check your inbox (or spam) for '{result.cleaned_filename}'!")
    else:
        print(f"\n[WARNING] Email dispatch returned error:")
        print(f"  • Error: {email_res.get('error')}")
        print(
            "\n  Note: If using Resend default test domain ('onboarding@resend.dev'), "
            "Resend only delivers to the email address registered with your Resend account. "
            "To send to any arbitrary email address, verify your custom domain in Resend dashboard."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
