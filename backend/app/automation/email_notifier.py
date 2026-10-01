"""TITAN Resend Email Notifier.

Sends cleaned datasets and interactive transformation audit reports
directly to the designated recipient via Resend API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import resend

from app.automation.headless_pipeline import HeadlessCleanResult
from app.config import settings
from app.logging import logger


def build_email_html_report(result: HeadlessCleanResult, trigger_info: str = "clean data") -> str:
    """Generates an HTML email summary report."""
    steps_rows = ""
    for step in result.steps_applied:
        transform_name = step.get("transformation", "Transform").replace("_", " ").title()
        steps_rows += f"""
        <tr style="border-bottom: 1px solid #1f2937;">
          <td style="padding: 10px 12px; color: #9ca3af; font-family: monospace; font-size: 13px;">#{step.get('seq', 1)}</td>
          <td style="padding: 10px 12px; color: #f3f4f6; font-weight: 500; font-size: 13px;">{transform_name}</td>
          <td style="padding: 10px 12px; color: #34d399; font-size: 13px; text-align: right;">{step.get('rows_removed', 0)} rows</td>
          <td style="padding: 10px 12px; color: #60a5fa; font-size: 13px; text-align: right;">{step.get('cells_modified', 0)} cells</td>
          <td style="padding: 10px 12px; color: #9ca3af; font-size: 12px; text-align: right;">{step.get('duration_ms', 0):.1f}ms</td>
        </tr>
        """

    if not steps_rows:
        steps_rows = """
        <tr>
          <td colspan="5" style="padding: 16px; text-align: center; color: #9ca3af; font-size: 13px;">
            Dataset was already clean. Verified types, schema integrity, and sanitized formulas.
          </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>TITAN Autonomous Clean Report</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e5e7eb;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0b0f19; padding: 32px 16px;">
        <tr>
          <td align="center">
            <table width="100%" style="max-width: 640px; background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);">
              
              <!-- Header -->
              <tr>
                <td style="background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); padding: 28px 32px; border-bottom: 1px solid #374151;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <span style="display: inline-block; background-color: #4338ca; color: #e0e7ff; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 4px 8px; border-radius: 6px; margin-bottom: 8px;">
                          Autonomous Pipeline
                        </span>
                        <h1 style="margin: 4px 0 0 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">
                          TITAN Data Cleaner
                        </h1>
                        <p style="margin: 6px 0 0 0; color: #9ca3af; font-size: 14px;">
                          Triggered by keyword: <code style="color: #60a5fa; background: #1e293b; padding: 2px 6px; border-radius: 4px;">"{trigger_info}"</code>
                        </p>
                      </td>
                      <td align="right" valign="top">
                        <span style="display: inline-block; background-color: #065f46; color: #6ee7b7; border: 1px solid #047857; font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 20px;">
                          ✓ Completed
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- Key Metrics Grid -->
              <tr>
                <td style="padding: 24px 32px;">
                  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                    <tr>
                      <td width="32%" style="background-color: #1f2937; border-radius: 8px; padding: 14px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; font-weight: 600;">Cleaned Rows</div>
                        <div style="color: #ffffff; font-size: 22px; font-weight: 700; margin-top: 4px;">{result.cleaned_rows:,}</div>
                        <div style="color: #34d399; font-size: 11px; margin-top: 2px;">from {result.initial_rows:,} initial</div>
                      </td>
                      <td width="2%"></td>
                      <td width="32%" style="background-color: #1f2937; border-radius: 8px; padding: 14px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; font-weight: 600;">Cells Standardized</div>
                        <div style="color: #60a5fa; font-size: 22px; font-weight: 700; margin-top: 4px;">{result.cells_modified:,}</div>
                        <div style="color: #9ca3af; font-size: 11px; margin-top: 2px;">{result.rows_dropped} rows dropped</div>
                      </td>
                      <td width="2%"></td>
                      <td width="32%" style="background-color: #1f2937; border-radius: 8px; padding: 14px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; font-weight: 600;">Execution Time</div>
                        <div style="color: #a78bfa; font-size: 22px; font-weight: 700; margin-top: 4px;">{result.duration_ms:.0f} ms</div>
                        <div style="color: #9ca3af; font-size: 11px; margin-top: 2px;">{len(result.steps_applied)} steps applied</div>
                      </td>
                    </tr>
                  </table>

                  <!-- File Details -->
                  <div style="background-color: #1e293b; border-left: 4px solid #6366f1; border-radius: 4px; padding: 12px 16px; margin-bottom: 24px;">
                    <table width="100%" cellpadding="2" cellspacing="0" style="font-size: 13px;">
                      <tr>
                        <td style="color: #9ca3af; width: 140px;">Original File:</td>
                        <td style="color: #f3f4f6; font-weight: 500;">{result.original_filename}</td>
                      </tr>
                      <tr>
                        <td style="color: #9ca3af;">Attached Clean File:</td>
                        <td style="color: #38bdf8; font-weight: 600;">{result.cleaned_filename}</td>
                      </tr>
                      <tr>
                        <td style="color: #9ca3af;">Clean Format:</td>
                        <td style="color: #e5e7eb; text-transform: uppercase;">{result.target_format}</td>
                      </tr>
                      <tr>
                        <td style="color: #9ca3af;">Canonical Hash:</td>
                        <td style="color: #9ca3af; font-family: monospace; font-size: 11px;">{result.cleaned_hash[:16]}...{result.cleaned_hash[-8:]}</td>
                      </tr>
                    </table>
                  </div>

                  <!-- Transformations Table -->
                  <h3 style="color: #ffffff; font-size: 15px; font-weight: 600; margin: 0 0 12px 0;">
                    Autonomous Transformation Steps
                  </h3>
                  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0f172a; border-radius: 8px; border: 1px solid #1f2937; margin-bottom: 24px; border-collapse: collapse;">
                    <thead>
                      <tr style="border-bottom: 1px solid #1f2937; background-color: #1e293b;">
                        <th style="padding: 8px 12px; color: #9ca3af; font-size: 11px; text-transform: uppercase; text-align: left;">#</th>
                        <th style="padding: 8px 12px; color: #9ca3af; font-size: 11px; text-transform: uppercase; text-align: left;">Transformation</th>
                        <th style="padding: 8px 12px; color: #9ca3af; font-size: 11px; text-transform: uppercase; text-align: right;">Rows Dropped</th>
                        <th style="padding: 8px 12px; color: #9ca3af; font-size: 11px; text-transform: uppercase; text-align: right;">Cells Edited</th>
                        <th style="padding: 8px 12px; color: #9ca3af; font-size: 11px; text-transform: uppercase; text-align: right;">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {steps_rows}
                    </tbody>
                  </table>

                  <!-- Information Callout -->
                  <div style="background-color: #111827; border: 1px solid #374151; border-radius: 8px; padding: 14px; font-size: 13px; color: #9ca3af; line-height: 1.5;">
                    <strong style="color: #f3f4f6;">✓ Attached and Ready:</strong>
                    Your cleaned file <strong>{result.cleaned_filename}</strong> is attached to this email. All dangerous spreadsheet formulas (CSV injection triggers) have been neutralized, internal tracking columns stripped, and data types verified.
                  </div>

                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background-color: #0f172a; padding: 18px 32px; border-top: 1px solid #1f2937; text-align: center; color: #6b7280; font-size: 12px;">
                  TITAN Autonomous Data Engine • Powered by Resend API • Zero Human Interactions Required
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    return html


def send_cleaned_dataset_email(
    to_email: str,
    result: HeadlessCleanResult,
    trigger_phrase: str = "clean data",
    custom_from: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delivers the cleaned dataset and HTML summary audit to the target recipient via Resend.
    """
    api_key = settings.RESEND_API_KEY
    if not api_key:
        err = "RESEND_API_KEY is not configured in backend settings"
        logger.error(f"[EmailNotifier] {err}")
        return {"success": False, "error": err}

    resend.api_key = api_key
    from_address = custom_from or settings.RESEND_FROM_EMAIL or "onboarding@resend.dev"

    # Format attachment: Resend python SDK accepts list of bytes/ints or base64 string
    attachment = {
        "filename": result.cleaned_filename,
        "content": list(result.cleaned_bytes),
    }

    html_content = build_email_html_report(result, trigger_info=trigger_phrase)
    subject = f"[TITAN] Cleaned Dataset: {result.cleaned_filename}"

    logger.info(
        f"[EmailNotifier] Sending cleaned file '{result.cleaned_filename}' "
        f"({len(result.cleaned_bytes)} bytes) to '{to_email}' via Resend (from '{from_address}')"
    )

    try:
        response = resend.Emails.send({
            "from": from_address,
            "to": [to_email.strip()],
            "subject": subject,
            "html": html_content,
            "attachments": [attachment],
        })
        email_id = getattr(response, "id", None) or (response.get("id") if isinstance(response, dict) else str(response))
        logger.info(f"[EmailNotifier] Successfully dispatched email via Resend: ID={email_id}")
        return {
            "success": True,
            "email_id": email_id,
            "recipient": to_email,
            "filename": result.cleaned_filename,
            "bytes_sent": len(result.cleaned_bytes),
        }
    except Exception as exc:
        logger.exception(f"[EmailNotifier] Resend delivery error: {exc}")
        return {
            "success": False,
            "error": str(exc),
            "recipient": to_email,
            "filename": result.cleaned_filename,
        }
