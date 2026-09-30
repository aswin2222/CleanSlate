"""Cloudinary integration service for storing dataset files securely."""
from __future__ import annotations

import base64
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("cleanslate.cloudinary")

CLOUD_NAME = "bgrvz383"
UPLOAD_PRESET = "TITAN-project"
UPLOAD_URL = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/raw/upload"


def upload_bytes_to_cloudinary(
    content: bytes,
    filename: str = "dataset.csv",
) -> Dict[str, Any]:
    """Uploads arbitrary binary/text file bytes to Cloudinary using the TITAN-project preset."""
    try:
        b64_content = base64.b64encode(content).decode("utf-8")
        data_uri = f"data:application/octet-stream;base64,{b64_content}"

        payload = urllib.parse.urlencode({
            "upload_preset": UPLOAD_PRESET,
            "file": data_uri,
        }).encode("utf-8")

        req = urllib.request.Request(
            UPLOAD_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            logger.info("Successfully uploaded %s to Cloudinary: %s", filename, resp_data.get("secure_url"))
            return {
                "secure_url": resp_data.get("secure_url", ""),
                "public_id": resp_data.get("public_id", ""),
                "bytes": resp_data.get("bytes", len(content)),
                "format": resp_data.get("format", filename.split(".")[-1]),
                "created_at": resp_data.get("created_at", ""),
            }
    except Exception as e:
        logger.error("Cloudinary upload failed: %s", e)
        return {
            "secure_url": "",
            "public_id": "",
            "bytes": len(content),
            "format": filename.split(".")[-1],
            "error": str(e),
        }
