# AgentWeave Visual Builder

A visual workflow automation platform for building, executing, and monitoring AI agent pipelines. Drag-and-drop node-based editor with real-time execution tracking.

## Features

- Visual workflow editor with drag-and-drop nodes (Agent, MCP Tool, Condition, Parallel, Feedback Loop)
- Multi-LLM support (OpenAI GPT-4o/o1, Anthropic Claude Sonnet/Haiku/Opus)
- MCP (Model Context Protocol) integration for 1000+ tool servers
- Real-time execution monitoring with token usage tracking
- Cron scheduling and webhook triggers
- A/B testing for workflow variants
- Encrypted secrets management with key rotation
- Version history and workflow snapshots
- Debug mode with breakpoints and state inspection

## Tech Stack

**Frontend**: React 19, TypeScript, Vite, @xyflow/react, Zustand, Radix UI, Tailwind CSS
**Backend**: FastAPI, SQLAlchemy (async), Pydantic, PyJWT
**Database**: SQLite (dev) / PostgreSQL (prod)
**Infrastructure**: Docker, Nginx, Alembic, GitHub Actions CI/CD

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+

### Frontend
```bash
npm install
npm run dev        # http://localhost:5173
```

### Backend
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # Configure API keys
uvicorn app.main:app --reload   # http://localhost:8000
```

### Docker (Production)
```bash
docker compose up -d
```

## Project Structure

```
visual-builder/
├── src/                    # Frontend (React + TypeScript)
│   ├── components/         # UI components (Blocks, Canvas, Layout, etc.)
│   ├── stores/             # Zustand state management
│   ├── services/           # API client
│   ├── types/              # TypeScript type definitions
│   └── constants/          # Model catalog, block definitions
├── backend/                # Backend (FastAPI)
│   ├── app/
│   │   ├── api/            # API endpoints (56 routes)
│   │   ├── core/           # Executor, MCP Manager, Scheduler
│   │   ├── models/         # SQLAlchemy models
│   │   ├── dtos/           # Pydantic DTOs
│   │   ├── services/       # Business logic
│   │   └── repositories/   # Data access layer
│   ├── tests/              # 313+ pytest tests
│   └── alembic/            # DB migrations
├── e2e/                    # Playwright E2E tests
├── nginx/                  # Reverse proxy config
└── docker-compose.yml      # Production deployment
```

## Testing

```bash
# Frontend (885 tests, 85%+ coverage)
npm test
npm run test:coverage

# Backend (313 tests)
cd backend && python -m pytest

# E2E
npm run test:e2e
```

## Environment Variables

See `.env.example` for all configuration options:
- `DATABASE_URL` - Database connection
- `JWT_SECRET` - Authentication secret
- `SECRET_KEY` - Encryption key for secrets
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - LLM provider keys
- `CORS_ORIGINS` - Allowed origins

## API Documentation

When running in development mode:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
