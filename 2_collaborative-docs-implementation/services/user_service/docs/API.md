# User Service API Documentation

## Endpoints

### POST /auth/register
- Register a new user.
- Request:
```json
{
  "email": "user@example.com",
  "password": "Test@1234",
  "full_name": "User Name"
}
```
- Response: 200 OK
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "User Name",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /auth/login
- Authenticate user and get tokens.
- Request (form):
```
username: user@example.com
password: Test@1234
```
- Response: 200 OK
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### GET /auth/me
- Get current user profile (requires Bearer token).

### PUT /auth/profile
- Update user profile (requires Bearer token).

### POST /auth/refresh
- Refresh JWT token using refresh token.

### POST /auth/logout
- Logout and invalidate refresh token.

### GET /health
- Health check endpoint.

## Authentication
- Use Bearer token in Authorization header for protected endpoints.

## Error Responses
- Standard error format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Description of the error."
  }
}
``` 