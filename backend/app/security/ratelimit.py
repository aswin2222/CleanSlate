"""API Rate Limiting configuration using slowapi."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter using client IP as key
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
