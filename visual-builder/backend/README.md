# Tool Hub Backend

A FastAPI-based visual workflow automation platform that enables building and executing complex workflows through a drag-and-drop interface with Model Context Protocol (MCP) integration.

## Quick Start

### Prerequisites

- Python 3.11+
- SQLite (development) or PostgreSQL 12+ (production)
- Git

### Installation

```bash
# Clone repository
cd visual-builder/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ../../  # Install agentchord core

# Set required environment variables
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export DATABASE_URL="sqlite:///./tool_hub.db"

# Run development server
python -m uvicorn app.main:app --reload
```

Server will be available at `http://localhost:8000`

### First Request

Generate a test JWT token:

```bash
python -c "from app.auth.jwt import create_access_token; print(create_access_token('user-1', 'user@example.com', 'user'))"
```

Test the API:

```bash
TOKEN="your-token-here"

# Check health
curl http://localhost:8000/health/live

# List workflows
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workflows
```

### Interactive Documentation

Open your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  API Layer (app/api/)                                   │
│  ├─ workflows.py      - Workflow CRUD                   │
│  ├─ executions.py     - Execution tracking              │
│  ├─ schedules.py      - Cron scheduling                 │
│  ├─ mcp.py            - MCP server management           │
│  ├─ secrets.py        - Secret management               │
│  ├─ versions.py       - Version control                 │
│  ├─ debug_ws.py       - WebSocket debugging             │
│  └─ webhooks.py       - Incoming webhooks               │
│                                                           │
│  Service Layer (app/services/)                          │
│  ├─ workflow_service.py - Business logic                │
│  ├─ execution_service.py - Execution orchestration      │
│  └─ audit_service.py    - Audit logging                 │
│                                                           │
│  Core Services (app/core/)                              │
│  ├─ executor.py       - Workflow execution engine       │
│  ├─ debug_executor.py - Debug mode executor            │
│  ├─ scheduler.py      - APScheduler wrapper             │
│  ├─ mcp_manager.py    - MCP server connections         │
│  ├─ secret_store.py   - Encrypted secret storage       │
│  ├─ version_store.py  - Version management             │
│  ├─ rbac.py           - Role-based access control      │
│  └─ pii_filter.py     - PII masking                    │
│                                                           │
│  Data Layer (app/)                                       │
│  ├─ models/           - SQLAlchemy ORM models          │
│  ├─ dtos/             - Pydantic request/response       │
│  ├─ repositories/     - Data access patterns            │
│  └─ db/               - Database initialization         │
│                                                           │
└─────────────────────────────────────────────────────────┘
         ↑                           ↑              ↑
      Users              Database         Webhooks
                     (SQLite/PostgreSQL)
```

### Key Design Patterns

1. **Dependency Injection** - FastAPI `Depends()` for clean testability
2. **Repository Pattern** - Abstracted data access layer
3. **Service Layer** - Business logic separation
4. **DTOs** - Pydantic models for validation and serialization
5. **Async/Await** - Native async support throughout
6. **Event-Driven** - Webhooks and audit logging

---

## Configuration

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET` | - | ✓ Yes | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | sqlite:///./tool_hub.db | No | Database connection string |
| `ENVIRONMENT` | development | No | Deployment environment |
| `CORS_ORIGINS` | http://localhost:5173 | No | Comma-separated allowed origins |
| `LOG_LEVEL` | INFO | No | Logging verbosity |
| `MCP_TIMEOUT` | 30 | No | MCP server timeout (seconds) |
| `EXECUTION_TIMEOUT` | 3600 | No | Workflow execution timeout |

### Database Configuration

**Development (SQLite)**:
```bash
export DATABASE_URL="sqlite:///./tool_hub.db"
```

**Production (PostgreSQL)**:
```bash
export DATABASE_URL="postgresql://user:password@host:5432/tool_hub"
```

Initialize database:
```bash
# Create tables
python -c "from app.db.database import init_db; init_db()"

# Run migrations (if using Alembic)
alembic upgrade head
```

### JWT Configuration

Generate a secure JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Token lifetime defaults to 1 hour. Modify in `app/auth/jwt.py`:
```python
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
```

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/                    # API endpoint routers
│   │   ├── workflows.py
│   │   ├── executions.py
│   │   ├── schedules.py
│   │   ├── mcp.py
│   │   ├── secrets.py
│   │   ├── versions.py
│   │   ├── debug_ws.py
│   │   └── webhooks.py
│   ├── services/               # Business logic
│   │   ├── workflow_service.py
│   │   ├── execution_service.py
│   │   └── audit_service.py
│   ├── core/                   # Core services
│   │   ├── executor.py
│   │   ├── debug_executor.py
│   │   ├── scheduler.py
│   │   ├── mcp_manager.py
│   │   ├── secret_store.py
│   │   ├── version_store.py
│   │   ├── rbac.py
│   │   └── pii_filter.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── workflow.py
│   │   ├── execution.py
│   │   ├── schedule.py
│   │   ├── secret.py
│   │   ├── mcp_server.py
│   │   ├── version.py
│   │   ├── webhook.py
│   │   └── audit_log.py
│   ├── dtos/                   # Pydantic request/response models
│   │   ├── workflow.py
│   │   ├── execution.py
│   │   ├── schedule.py
│   │   ├── secret.py
│   │   ├── mcp.py
│   │   ├── version.py
│   │   ├── debug.py
│   │   └── ab_test.py
│   ├── repositories/           # Data access layer
│   │   ├── workflow_repo.py
│   │   ├── execution_repo.py
│   │   ├── schedule_repo.py
│   │   └── version_repo.py
│   ├── auth/                   # Authentication
│   │   ├── jwt.py
│   │   └── __init__.py
│   ├── db/                     # Database setup
│   │   ├── database.py
│   │   └── __init__.py
│   └── data/                   # Static data
│       └── mcp_catalog.py
├── tests/
│   ├── test_workflows_api.py
│   ├── test_executions_api.py
│   ├── test_execution_service.py
│   ├── test_scheduler.py
│   ├── conftest.py
│   └── ...
├── docs/
│   ├── RUNBOOK.md              # Operations guide
│   ├── DISASTER_RECOVERY.md    # Disaster recovery
│   ├── API_QUICK_REFERENCE.md  # API reference
│   └── README.md               # This file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
└── README.md
```

---

## API Documentation

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.example.com`

### Key Endpoints

#### Workflows
- `GET /api/workflows` - List workflows
- `POST /api/workflows` - Create workflow
- `GET /api/workflows/{id}` - Get workflow
- `PUT /api/workflows/{id}` - Update workflow
- `DELETE /api/workflows/{id}` - Delete workflow
- `POST /api/workflows/{id}/run` - Execute workflow
- `POST /api/workflows/{id}/validate` - Validate workflow

#### Executions
- `GET /api/executions` - List executions
- `GET /api/executions/{id}` - Get execution details
- `POST /api/executions/{id}/stop` - Stop execution
- `POST /api/executions/{id}/resume` - Resume from breakpoint
- `GET /api/executions/{id}/logs` - Get execution logs

#### Schedules
- `GET /api/schedules` - List schedules
- `POST /api/schedules` - Create schedule
- `PUT /api/schedules/{id}` - Update schedule
- `DELETE /api/schedules/{id}` - Delete schedule

#### MCP Servers
- `GET /api/mcp/servers` - List servers
- `POST /api/mcp/servers` - Connect server
- `GET /api/mcp/servers/{id}/tools` - List tools
- `GET /api/mcp/servers/{id}/health` - Health check

#### Secrets
- `GET /api/secrets` - List secrets
- `POST /api/secrets` - Create secret
- `PUT /api/secrets/{name}` - Update secret
- `DELETE /api/secrets/{name}` - Delete secret

#### Health
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /health/mcp/{server_id}` - MCP health

**Full documentation**: See [API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md)

**Interactive documentation** (when server running):
- **Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Development Guide

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_workflows_api.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run async tests
pytest tests/ -v -m asyncio
```

### Code Style

Code follows PEP 8 with Black formatter:

```bash
# Install dev dependencies
pip install black flake8 mypy

# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

### Adding New Endpoints

1. **Create DTO** in `app/dtos/`:
```python
from pydantic import BaseModel

class MyRequestDTO(BaseModel):
    field: str
```

2. **Create API route** in `app/api/`:
```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/resource", tags=["resource"])

@router.post("")
async def create_resource(
    data: MyRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
):
    """Create a new resource."""
    return {"id": "res-123"}
```

3. **Include router** in `app/main.py`:
```python
from .api import my_router
app.include_router(my_router.router)
```

4. **Add tests** in `tests/`:
```python
@pytest.mark.asyncio
async def test_create_resource(client, auth_headers):
    response = client.post("/api/resource", json={"field": "value"})
    assert response.status_code == 201
```

---

## Deployment

### Docker

Build and run:

```bash
# Build image
docker build -t tool-hub-backend .

# Run container
docker run -p 8000:8000 \
  -e JWT_SECRET="your-secret" \
  -e DATABASE_URL="sqlite:///./tool_hub.db" \
  tool-hub-backend
```

See `Dockerfile` for production optimizations.

### Kubernetes

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tool-hub-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tool-hub-backend
  template:
    metadata:
      labels:
        app: tool-hub-backend
    spec:
      containers:
      - name: api
        image: tool-hub-backend:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: tool-hub-secrets
              key: jwt-secret
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: tool-hub-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Production Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Set JWT_SECRET to cryptographically random value
- [ ] Enable HTTPS
- [ ] Configure CORS_ORIGINS for your domain
- [ ] Set ENVIRONMENT=production
- [ ] Setup database backups
- [ ] Configure logging aggregation
- [ ] Setup monitoring and alerting
- [ ] Configure health check endpoints
- [ ] Test disaster recovery procedures

See [RUNBOOK.md](docs/RUNBOOK.md) for complete operations guide.

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
python -m uvicorn app.main:app --port 8001
```

### JWT Secret Not Set

```bash
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
python -m uvicorn app.main:app --reload
```

### Database Connection Error

```bash
# Check SQLite database exists
ls -la tool_hub.db

# Initialize if missing
python -c "from app.db.database import init_db; init_db()"

# For PostgreSQL, verify credentials
psql -U user -h localhost -d tool_hub -c "SELECT 1;"
```

### Scheduler Not Starting

```bash
# Check logs
tail -f app.log

# Verify database connectivity
python -c "from app.db.database import get_session_factory; sf = get_session_factory()"

# Restart service
python -m uvicorn app.main:app --reload
```

---

## Operations

### Monitoring

Check service health:

```bash
# Liveness
curl http://localhost:8000/health/live

# Readiness
curl http://localhost:8000/health/ready
```

View logs:

```bash
# Real-time logs
tail -f app.log

# Search logs
grep "ERROR" app.log

# Last 100 lines
tail -100 app.log
```

### Database Maintenance

```bash
# Backup database
cp tool_hub.db tool_hub.db.backup.$(date +%Y%m%d)

# Analyze query performance (SQLite)
sqlite3 tool_hub.db "ANALYZE;"

# Cleanup old data
sqlite3 tool_hub.db "DELETE FROM executions WHERE created_at < datetime('now', '-90 days');"
```

### Scaling

For high-traffic environments:

1. **Use PostgreSQL** instead of SQLite
2. **Add Redis** for distributed execution queue
3. **Scale horizontally** with multiple application instances
4. **Configure load balancer** to distribute requests
5. **Setup connection pooling** for database

---

## Contributing

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes following code style (see above)
3. Add tests for new functionality
4. Ensure all tests pass: `pytest tests/`
5. Submit pull request with description

### Commit Guidelines

```
[FEATURE] Add new API endpoint for X
[FIX] Resolve issue with Y
[DOCS] Update README
[TEST] Add tests for feature Z
```

---

## License

See `LICENSE` file in repository root.

---

## Support

### Documentation

- **API Reference**: [API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md)
- **Operations Guide**: [RUNBOOK.md](docs/RUNBOOK.md)
- **Disaster Recovery**: [DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md)
- **Interactive Docs**: http://localhost:8000/docs

### Getting Help

- Check existing GitHub issues
- Review error logs in `app.log`
- Check [Troubleshooting](#troubleshooting) section above

---

## Roadmap

### Phase 1 (Current)
- ✅ Core API structure
- ✅ JWT authentication
- ✅ Workflow CRUD
- ✅ Basic execution
- ✅ Scheduler support

### Phase 2 (Planned)
- ⏳ MCP server integration
- ⏳ Distributed execution (Celery)
- ⏳ Advanced debugging features
- ⏳ Workflow templates library

### Phase 3 (Future)
- 🔮 Multi-tenancy
- 🔮 Advanced analytics
- 🔮 Custom node types
- 🔮 Workflow marketplace

---

## Related Projects

- **Visual Builder Frontend**: `../../visual-builder/src`
- **AgentChord Core**: `../../agentchord/core`
- **MCP Specification**: https://spec.modelcontextprotocol.io

---

**Version**: 1.0.0
**Last Updated**: 2024-01-15
**Maintainers**: Backend Team
