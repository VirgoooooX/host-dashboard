"""Authentication handler — password hash, JWT, login rate limiting.

Uses pwdlib[argon2] for password hashing and PyJWT for token management.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash

from app.config import get_settings

# ── Password hashing ─────────────────────────────────────────────────────

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plain-text password with Argon2 (recommended)."""
    return password_hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its Argon2 hash."""
    return password_hasher.verify(plain, hashed)


# ── JWT ─────────────────────────────────────────────────────────────────

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(username: str) -> str:
    """Create a JWT access token with username claim and expiration."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Decode a JWT token and return the username. Returns None on any error."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> str:
    """FastAPI dependency: extract and validate the current user from Bearer token.

    Uses explicit Depends(security_scheme) injection so FastAPI reads the
    Authorization: Bearer header and returns 401 on missing/invalid token.

    Returns the username string on success.
    """
    err_detail = "Not authenticated"
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err_detail,
        )
    username = decode_access_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


# ── Login rate limiter (in-memory, single-worker) ──────────────────────
# Future: replace with SQLite-backed window when switching to >1 worker.


class LoginRateLimiter:
    """Simple sliding-window login rate limiter.

    Allows up to `max_attempts` failed logins per `window_seconds`.
    The window is per-IP-address in-memory.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self._max = max_attempts
        self._window = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def record_failure(self, ip: str) -> bool:
        """Record a failed login attempt. Returns True if the IP is now blocked."""
        now = time.monotonic()
        window_start = now - self._window
        entries = self._attempts.setdefault(ip, [])
        # Purge old entries
        self._attempts[ip] = [t for t in entries if t > window_start]
        self._attempts[ip].append(now)
        return len(self._attempts[ip]) > self._max

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently rate-limited."""
        now = time.monotonic()
        window_start = now - self._window
        entries = self._attempts.get(ip, [])
        valid = [t for t in entries if t > window_start]
        self._attempts[ip] = valid
        return len(valid) > self._max

    def clear(self, ip: str) -> None:
        """Clear all failed attempts for a given IP (e.g. after successful login)."""
        self._attempts.pop(ip, None)


rate_limiter = LoginRateLimiter()
