import re
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from typing import Callable

# --- Password Complexity ---
def is_password_complex(password: str) -> bool:
    # At least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
    return bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password))

# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        response: Response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        return response

# --- Audit Logging ---
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('audit.log')
audit_logger.setLevel(logging.INFO)
audit_logger.addHandler(audit_handler)

def log_security_event(event: str, user: str = None, ip: str = None):
    audit_logger.info(f"event={event} user={user} ip={ip}")

# --- Account Lockout ---
class AccountLockoutManager:
    def __init__(self, redis, max_attempts=5, lockout_seconds=900):
        self.redis = redis
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds

    async def record_failed_attempt(self, email: str):
        key = f"lockout:{email}"
        attempts = await self.redis.incr(key)
        if attempts == 1:
            await self.redis.expire(key, self.lockout_seconds)
        return attempts

    async def is_locked(self, email: str):
        key = f"lockout:{email}"
        attempts = await self.redis.get(key)
        if attempts and int(attempts) >= self.max_attempts:
            return True
        return False

    async def reset_attempts(self, email: str):
        key = f"lockout:{email}"
        await self.redis.delete(key) 