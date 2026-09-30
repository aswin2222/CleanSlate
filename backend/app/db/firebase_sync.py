"""Firebase Firestore real-time synchronization service."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("cleanslate.firebase")

PROJECT_ID = "titan-d57bf"
API_KEY = "AIzaSyAWWv4W26C4mNeiKfzbMy8jMhsYi-pjKA0"
BASE_FIRESTORE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
)


def _convert_value_to_firestore(val: Any) -> Dict[str, Any]:
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, (list, tuple)):
        return {"arrayValue": {"values": [_convert_value_to_firestore(v) for v in val]}}
    if isinstance(val, dict):
        return {
            "mapValue": {
                "fields": {k: _convert_value_to_firestore(v) for k, v in val.items()}
            }
        }
    return {"stringValue": str(val)}


def save_firestore_document(
    collection: str,
    document_id: Optional[str],
    data: Dict[str, Any],
) -> Optional[str]:
    """Writes or patches a document in Firestore."""
    try:
        fields = {k: _convert_value_to_firestore(v) for k, v in data.items()}
        body = json.dumps({"fields": fields}).encode("utf-8")

        if document_id:
            url = f"{BASE_FIRESTORE_URL}/{collection}/{document_id}?key={API_KEY}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="PATCH",
            )
        else:
            url = f"{BASE_FIRESTORE_URL}/{collection}?key={API_KEY}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            doc_name = resp_data.get("name", "")
            logger.info("Saved Firestore doc in %s: %s", collection, doc_name)
            return doc_name
    except Exception as e:
        logger.warning("Firestore document write failed for %s: %s", collection, e)
        return None


def sync_dataset_to_firestore(dataset_dict: Dict[str, Any]) -> None:
    doc_id = dataset_dict.get("id")
    save_firestore_document("datasets", doc_id, dataset_dict)


def sync_run_to_firestore(run_dict: Dict[str, Any]) -> None:
    doc_id = run_dict.get("id")
    save_firestore_document("runs", doc_id, run_dict)


def sync_audit_to_firestore(audit_dict: Dict[str, Any]) -> None:
    save_firestore_document("audit_logs", None, audit_dict)
