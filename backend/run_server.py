#!/usr/bin/env python3
"""
FastAPI server runner for TripWeaver Backend
"""

import uvicorn
from app.api import app

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
