# Configuration Guide

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry (default: 7)

## Database
- Uses PostgreSQL with SQLAlchemy async engine.
- Run migrations before starting the service.

## Redis
- Used for session, refresh tokens, rate limiting, and lockout state.

## Security
- Adjust rate limiting and lockout parameters in `security.py` as needed. 