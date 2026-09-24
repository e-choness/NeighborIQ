"""Per-client rate limits (in-memory: fine for one API replica; use Redis storage when scaling out)."""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "120/minute")],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
)
