# Development Workflow

## Branching
- Use feature branches for new features
- Use `main` or `master` for production

## Testing
- Write unit and integration tests for all new code
- Run `bash scripts/test_integration.sh` before PRs
- Use `python scripts/load_test_ws.py` for load testing

## Code Review
- All code changes require PR and review
- Follow code style and documentation standards

## Deployment
- Use Docker Compose for local and staging
- Use CI/CD for automated testing and deployment
- Run migrations before deploying new DB changes

## Environment
- Use `.env` files for configuration
- Use `scripts/setup_local.sh` for local setup 