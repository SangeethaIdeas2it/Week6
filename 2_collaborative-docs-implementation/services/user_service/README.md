# User Service

A production-ready microservice for user management in a collaborative document system.

## Features
- FastAPI async application
- User registration, login, profile management
- JWT authentication with refresh tokens
- Password hashing (bcrypt) and complexity enforcement
- PostgreSQL (SQLAlchemy async)
- Redis for session, rate limiting, and lockout
- Security headers, audit logging, CORS
- Account lockout after failed attempts
- Comprehensive error handling
- OpenAPI docs

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure environment variables (see `docs/CONFIGURATION.md`).
3. Run database migrations.
4. Start the service:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Security
- See `docs/SECURITY.md` for implementation details.

## Testing
- Run all tests:
  ```bash
  pytest
  ```
- See `tests/` for unit, integration, and security tests.

## Documentation
- [API Reference](docs/API.md)
- [Security](docs/SECURITY.md)
- [Configuration](docs/CONFIGURATION.md)
- [Deployment](docs/DEPLOYMENT.md) 