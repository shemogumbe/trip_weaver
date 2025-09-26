"""MongoDB client and helpers for logging trip requests and results.

This module uses pymongo synchronously and safely no-ops when MONGODB_URI
is not configured, so it won't break local runs or CI.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, Optional

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
except Exception:  # pragma: no cover - optional until installed in prod
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore


logger = logging.getLogger(__name__)

_client: Optional[MongoClient] = None  # type: ignore


def _get_mongo_uri() -> Optional[str]:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return None
    return uri


def get_mongo_client() -> Optional[MongoClient]:  # type: ignore
    global _client
    if _client is not None:
        return _client
    uri = _get_mongo_uri()
    if not uri or MongoClient is None:
        if not uri:
            logger.warning("MONGODB_URI not set; Mongo logging disabled")
        else:
            logger.warning("pymongo not installed; Mongo logging disabled")
        return None
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return _client


def get_collection(name: str) -> Optional[Collection]:  # type: ignore
    client = get_mongo_client()
    if client is None:
        return None
    db_name = os.getenv("MONGODB_DB", "tripweaver")
    return client[db_name][name]


def log_trip_request(payload: Dict[str, Any]) -> Optional[str]:
    """Insert a new trip request document. Returns inserted id as str or None."""
    col = get_collection("trip_requests")
    if col is None:
        return None
    doc = {
        **payload,
        "created_at": int(time.time()),
        "status": payload.get("status", "started"),
    }
    res = col.insert_one(doc)
    return str(res.inserted_id)


def update_trip_result(request_id: Optional[str], update: Dict[str, Any]) -> None:
    """Update the request document with final result or error info."""
    col = get_collection("trip_requests")
    if col is None or not request_id:
        return
    try:
        from bson import ObjectId  # type: ignore
        oid = ObjectId(request_id)
    except Exception:
        logger.warning("Invalid request_id for Mongo update; skipping")
        return
    patch = {**update, "updated_at": int(time.time())}
    col.update_one({"_id": oid}, {"$set": patch})
