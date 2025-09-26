#!/usr/bin/env python3
# Moved from backend/test_api.py
# See README_API.md for usage. This script calls the async /plan-trip endpoint.

import requests
import json

BASE_URL = "http://localhost:8000"

if __name__ == "__main__":
    req = {
        "origin": "NBO",
        "destination": "Dubai",
        "start_date": "2025-11-10",
        "end_date": "2025-11-16",
        "hobbies": ["night life", "fine dining", "golf"],
        "adults": 2,
        "budget_level": "mid",
        "trip_type": "honeymoon",
        "constraints": {}
    }
    r = requests.post(f"{BASE_URL}/plan-trip", json=req)
    print(r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
