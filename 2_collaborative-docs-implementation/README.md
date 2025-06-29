# Collaborative Document Microservices System

## Architecture Overview
- **User Service**: Authentication, user management, JWT, account security
- **Document Service**: Document CRUD, versioning, sharing, search
- **Collaboration Service**: Real-time editing, WebSocket, operational transformation
- **API Gateway**: NGINX for routing and WebSocket proxy
- **PostgreSQL**: Persistent storage
- **Redis**: Caching, session, event streaming

## Quick Start
1. Clone the repo
2. Copy `.env.example` to `.env` and adjust as needed
3. Run migrations:
   ```bash
   bash scripts/migrate.sh
   ```
4. Start all services:
   ```bash
   docker-compose up --build
   ```
5. Run tests:
   ```bash
   bash scripts/test_integration.sh
   ```
6. Load test WebSocket:
   ```bash
   python scripts/load_test_ws.py
   ```

## Development
- Use `scripts/setup_local.sh` for local setup
- All service code in `services/`
- Shared models in `shared/`
- API Gateway config in `nginx.conf`

## Monitoring & Debugging
- Health endpoints: `/health` on each service
- Logs: stdout and `audit.log` (security events)
- Metrics: integrate with Prometheus/Grafana as needed

## Documentation
- API docs: see each service's `/docs` endpoint
- Architecture: `system-context.md`, `architecture-design.md`
- Deployment: `docs/DEPLOYMENT.md`
- Security: `docs/SECURITY.md`

## Contributing
- See `docs/DEVELOPMENT.md` for workflow and guidelines 