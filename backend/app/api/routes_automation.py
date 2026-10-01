"""TITAN Email Automation Router.

Provides endpoints for inbound email webhooks, direct headless cleaning triggers,
and Resend email dispatch integration.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr

from app.automation.email_notifier import send_cleaned_dataset_email
from app.automation.headless_pipeline import clean_dataset_headless
from app.config import settings
from app.logging import logger

automation_router = APIRouter(prefix="/automation", tags=["Automation"])

TRIGGER_PHRASE = "clean data"


class StatusResponse(BaseModel):
    resend_configured: bool
    resend_from_email: str
    trigger_keyword: str
    supported_formats: list[str]


@automation_router.get("/status", response_model=StatusResponse)
def get_automation_status() -> StatusResponse:
    """Returns the current readiness status of the email automation pipeline."""
    return StatusResponse(
        resend_configured=bool(settings.RESEND_API_KEY),
        resend_from_email=settings.RESEND_FROM_EMAIL,
        trigger_keyword=TRIGGER_PHRASE,
        supported_formats=["csv", "xlsx", "xls", "tsv", "json", "parquet"],
    )


@automation_router.post("/trigger-clean")
async def trigger_clean_direct(
    recipient_email: str = Form(..., description="Target email address to receive cleaned file"),
    trigger_text: str = Form("clean data", description="Trigger phrase (must contain 'clean data')"),
    file: UploadFile = File(..., description="Messy dataset file to clean"),
    bypass_trigger_check: bool = Form(False, description="Whether to bypass keyword check for direct testing"),
) -> Dict[str, Any]:
    """
    Direct endpoint to trigger the autonomous cleaning pipeline and dispatch the
    cleaned dataset to the specified recipient email via Resend.
    """
    # 1. Trigger phrase validation
    if not bypass_trigger_check and TRIGGER_PHRASE not in trigger_text.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Automation trigger phrase '{TRIGGER_PHRASE}' not found in trigger text: '{trigger_text}'",
        )

    # 2. Ingest raw bytes
    filename = file.filename or "dataset.csv"
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 3. Headless Pipeline Execution
    result = clean_dataset_headless(file_bytes=raw_bytes, original_filename=filename)
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Autonomous cleaning failed: {result.error_message}")

    # 4. Resend Email Dispatch
    email_res = send_cleaned_dataset_email(
        to_email=recipient_email,
        result=result,
        trigger_phrase=trigger_text,
    )

    return {
        "status": "success",
        "run_id": result.run_id,
        "original_filename": result.original_filename,
        "cleaned_filename": result.cleaned_filename,
        "format": result.target_format,
        "initial_rows": result.initial_rows,
        "cleaned_rows": result.cleaned_rows,
        "rows_dropped": result.rows_dropped,
        "cells_modified": result.cells_modified,
        "steps_count": len(result.steps_applied),
        "steps": result.steps_applied,
        "initial_hash": result.initial_hash,
        "cleaned_hash": result.cleaned_hash,
        "duration_ms": result.duration_ms,
        "email_delivery": email_res,
    }


@automation_router.post("/email-webhook")
async def handle_email_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Inbound email webhook handler.
    Can be invoked by an email parser (Cloudflare Email Worker, SendGrid Inbound Parse,
    Postmark, local forwarder, or Zapier/Make webhook).

    Extracts:
    - Attached dataset file
    - Trigger phrase ('clean data' in subject or body)
    - Target recipient email
    """
    content_type = request.headers.get("content-type", "").lower()
    file_bytes: Optional[bytes] = None
    filename = "dataset.csv"
    subject = ""
    body = ""
    from_email = ""
    destination_email = ""

    if "multipart/form-data" in content_type:
        form = await request.form()
        subject = str(form.get("subject", ""))
        body = str(form.get("text", "") or form.get("body", "") or form.get("html", ""))
        from_email = str(form.get("from", "") or form.get("sender", ""))
        destination_email = str(
            form.get("destination_email", "")
            or form.get("to_email", "")
            or form.get("to", "")
            or from_email
        )

        # Check for uploaded attachment
        for key in ("file", "attachment", "attachments", "attachment1"):
            form_val = form.get(key)
            if hasattr(form_val, "read") and hasattr(form_val, "filename"):
                file_bytes = await form_val.read()
                filename = form_val.filename or filename
                break

    elif "application/json" in content_type:
        payload = await request.json()
        subject = payload.get("subject", "")
        body = payload.get("text", "") or payload.get("body", "") or payload.get("html", "")
        from_email = payload.get("from", "") or payload.get("sender", "")
        destination_email = payload.get("destination_email") or payload.get("to_email") or from_email
        filename = payload.get("filename", "dataset.csv")

        # Support base64 encoded attachment in JSON
        b64_content = payload.get("file_base64") or payload.get("attachment_base64")
        if b64_content:
            try:
                file_bytes = base64.b64decode(b64_content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 attachment: {e}")

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported media type. Send multipart/form-data or application/json.",
        )

    # 1. Trigger phrase check
    combined_text = f"{subject} {body}".lower()
    if TRIGGER_PHRASE not in combined_text:
        logger.info(f"[EmailWebhook] Ignored email: keyword '{TRIGGER_PHRASE}' not found in subject/body.")
        return {
            "status": "ignored",
            "message": f"Keyword '{TRIGGER_PHRASE}' not found in email subject or body.",
            "subject": subject,
        }

    # 2. Validate attachment
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="No dataset attachment found in email payload.",
        )

    # 3. Validate recipient
    target_recipient = destination_email.strip()
    if not target_recipient or "@" not in target_recipient:
        raise HTTPException(
            status_code=400,
            detail="No valid destination email found in webhook payload.",
        )

    logger.info(
        f"[EmailWebhook] Trigger '{TRIGGER_PHRASE}' matched for '{filename}'! "
        f"Processing headless pipeline for recipient '{target_recipient}'."
    )

    # 4. Execute pipeline and send email
    # For webhooks, we run in background or return summary
    result = clean_dataset_headless(file_bytes=file_bytes, original_filename=filename)
    if not result.success:
        return {
            "status": "error",
            "message": f"Cleaning failed: {result.error_message}",
            "filename": filename,
        }

    email_delivery = send_cleaned_dataset_email(
        to_email=target_recipient,
        result=result,
        trigger_phrase=subject or TRIGGER_PHRASE,
    )

    return {
        "status": "processed",
        "trigger": TRIGGER_PHRASE,
        "recipient": target_recipient,
        "run_id": result.run_id,
        "cleaned_filename": result.cleaned_filename,
        "rows_initial": result.initial_rows,
        "rows_cleaned": result.cleaned_rows,
        "cells_modified": result.cells_modified,
        "duration_ms": result.duration_ms,
        "email_delivery": email_delivery,
    }
