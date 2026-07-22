"""
app/core/limiter.py

Shared rate-limiter instance (slowapi), keyed by client IP.
Import `limiter` in any router that needs @limiter.limit(...).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)