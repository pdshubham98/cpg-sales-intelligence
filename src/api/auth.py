"""
Optional API key authentication.
Set SECRET_KEY env var to enable. If unset, auth is bypassed (dev/demo mode).
"""
import os
import logging
from typing import Optional
from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        return  # auth disabled — dev/demo mode
    if x_api_key != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")
