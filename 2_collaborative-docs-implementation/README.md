# Collaborative Document Microservices System

## Architecture Overview
- **API Gateway**: Intelligent routing, authentication, rate limiting (Port 80)
- **User Service**: Authentication, user management, JWT, account security (Port 8003)
- **Document Service**: Document CRUD, versioning, sharing, search (Port 8001)
- **Collaboration Service**: Real-time editing, WebSocket, operational transformation (Port 8002)
- **PostgreSQL**: Persistent storage (Port 5432)
- **Redis**: Caching, session, event streaming (Port 6379)

## Port Configuration
- **API Gateway**: http://localhost:80 (or http://localhost:8000 for direct access)
- **User Service**: http://localhost:8003
- **Document Service**: http://localhost:8001
- **Collaboration Service**: http://localhost:8002
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Quick Start

### Option 1: Docker Compose (Recommended)
1. Clone the repo
2. Copy `.env.example` to `.env` and adjust as needed
3. Start all services:
   ```bash
   docker-compose up --build
   ```
4. Access the system:
   - API Gateway: http://localhost
   - API Documentation: http://localhost/docs
   - Health Check: http://localhost/api/v1/health

### Option 2: Individual Services
1. Install dependencies:
   ```bash
   pip install -r services/user_service/requirements.txt
   pip install -r services/document_service/requirements.txt
   pip install -r services/collaboration_service/requirements.txt
   pip install -r integration/requirements.txt
   ```
2. Start services individually:
   ```bash
   # Terminal 1: User Service
   cd services/user_service && python main.py
   
   # Terminal 2: Document Service  
   cd services/document_service && python main.py
   
   # Terminal 3: Collaboration Service
   cd services/collaboration_service && python main.py
   
   # Terminal 4: API Gateway
   cd integration && python api_gateway.py
   ```

## Development
- Use `scripts/setup_local.sh` for local setup
- All service code in `services/`
- Shared models in `shared/`
- API Gateway in `integration/`

## Monitoring & Debugging
- Health endpoints: `/health` on each service
- API Gateway health: http://localhost/api/v1/health
- API Gateway metrics: http://localhost/api/v1/metrics
- Logs: stdout and `audit.log` (security events)
- Metrics: integrate with Prometheus/Grafana as needed

## Documentation
- API docs: see each service's `/docs` endpoint
- Architecture: `system-context.md`, `architecture-design.md`
- Deployment: `docs/DEPLOYMENT.md`
- Security: `docs/SECURITY.md`

## Contributing
- See `docs/DEVELOPMENT.md` for workflow and guidelines 