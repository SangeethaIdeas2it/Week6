# Security Implementation Details

## Rate Limiting
- Authentication endpoints are rate-limited per IP using Redis.
- Exceeding the limit returns HTTP 429.

## Password Complexity
- Passwords must be at least 8 characters, with uppercase, lowercase, digit, and special character.

## Security Headers
- X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Strict-Transport-Security are set on all responses.

## Audit Logging
- Security events (login, logout, failed attempts, lockouts) are logged to `audit.log`.

## Account Lockout
- After 5 failed login attempts, the account is locked for 15 minutes.

## Session Management
- Refresh tokens and lockout state are managed in Redis.

## Input Validation
- All inputs are validated with Pydantic and sanitized.

## CORS
- CORS is configured to allow only trusted origins in production. 