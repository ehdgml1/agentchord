# API Endpoints Summary - Phase 0 MVP

## Quick Reference

### Workflows API (`/api/workflows`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/workflows` | 200 | List workflows (paginated) |
| POST | `/api/workflows` | 201 | Create new workflow |
| GET | `/api/workflows/:id` | 200 | Get workflow details |
| PUT | `/api/workflows/:id` | 200 | Update workflow |
| DELETE | `/api/workflows/:id` | 204 | Delete workflow |
| POST | `/api/workflows/:id/run` | 200 | Execute workflow |
| POST | `/api/workflows/:id/validate` | 200 | Validate workflow structure |

**Total:** 7 endpoints

### Executions API (`/api/executions`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/executions` | 200 | List executions (filterable) |
| GET | `/api/executions/:id` | 200 | Get execution with logs |
| POST | `/api/executions/:id/stop` | 200 | Stop running execution |
| POST | `/api/executions/:id/resume` | 200 | Resume paused execution |
| GET | `/api/executions/:id/logs` | 200 | Get execution node logs |

**Total:** 5 endpoints

### MCP Servers API (`/api/mcp/servers`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/mcp/servers` | 200 | List connected servers |
| POST | `/api/mcp/servers` | 201 | Connect new server |
| DELETE | `/api/mcp/servers/:id` | 204 | Disconnect server |
| GET | `/api/mcp/servers/:id/tools` | 200 | List available tools |
| GET | `/api/mcp/servers/:id/health` | 200 | Check server health |

**Total:** 5 endpoints

### Secrets API (`/api/secrets`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/secrets` | 200 | List secret names |
| POST | `/api/secrets` | 201 | Create new secret |
| PUT | `/api/secrets/:name` | 200 | Update secret value |
| DELETE | `/api/secrets/:name` | 204 | Delete secret |

**Total:** 4 endpoints

### Webhooks API (`/webhook`) - Phase -1
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/webhook/:webhook_id` | 200 | Handle incoming webhook |
| GET | `/webhook` | 200 | List webhooks |
| POST | `/webhook` | 201 | Create webhook |
| GET | `/webhook/:webhook_id` | 200 | Get webhook details |
| DELETE | `/webhook/:webhook_id` | 204 | Delete webhook |
| POST | `/webhook/:webhook_id/rotate` | 200 | Rotate webhook secret |

**Total:** 6 endpoints (existing)

### Health Checks (`/health`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/health/live` | 200 | Liveness probe |
| GET | `/health/ready` | 200 | Readiness probe |
| GET | `/health/mcp/:server_id` | 200 | MCP server health |

**Total:** 3 endpoints (existing)

---

## Total API Endpoints: 30

### By Status Code
- **200 OK**: 17 endpoints (read operations, actions)
- **201 Created**: 4 endpoints (create operations)
- **204 No Content**: 5 endpoints (delete operations)

### By Category
- **Workflows**: 7 endpoints
- **Executions**: 5 endpoints
- **MCP Servers**: 5 endpoints
- **Secrets**: 4 endpoints
- **Webhooks**: 6 endpoints (existing)
- **Health**: 3 endpoints (existing)

### Authentication
- **Protected**: 21 endpoints (require JWT)
- **Public**: 9 endpoints (health checks, webhooks with signature)

---

## Error Codes

### 4xx Client Errors
| Code | Error Code | Description |
|------|------------|-------------|
| 400 | `WEBHOOK_PAYLOAD_INVALID` | Invalid JSON payload |
| 400 | `WEBHOOK_DISABLED` | Webhook is disabled |
| 400 | Various | Invalid request (execution not stoppable, etc.) |
| 401 | `INVALID_TOKEN` | JWT token invalid or expired |
| 401 | `WEBHOOK_SIGNATURE_INVALID` | Webhook signature mismatch |
| 401 | `WEBHOOK_HEADERS_MISSING` | Missing required webhook headers |
| 403 | `WEBHOOK_IP_NOT_ALLOWED` | IP not in allowlist |
| 404 | `WORKFLOW_NOT_FOUND` | Workflow doesn't exist |
| 404 | `EXECUTION_NOT_FOUND` | Execution doesn't exist |
| 404 | `SERVER_NOT_FOUND` | MCP server doesn't exist |
| 404 | `SECRET_NOT_FOUND` | Secret doesn't exist |
| 404 | `WEBHOOK_NOT_FOUND` | Webhook doesn't exist |

### 5xx Server Errors
| Code | Error Code | Description |
|------|------------|-------------|
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 501 | `NOT_IMPLEMENTED` | Feature not yet implemented |

---

## Response Time Targets

| Endpoint Type | Target | Description |
|---------------|--------|-------------|
| List (paginated) | < 100ms | Database query with limit |
| Get by ID | < 50ms | Single record fetch |
| Create | < 200ms | Insert + validation |
| Update | < 200ms | Update + validation |
| Delete | < 100ms | Soft/hard delete |
| Execute workflow | < 500ms | Queue + return immediately |
| Stop/Resume | < 100ms | State update |
| Health checks | < 50ms | Quick status check |

---

## Data Flow

### Create Workflow
```
Client → POST /api/workflows → JWT Auth → Validate Input → Service Layer → Database → Response
```

### Execute Workflow
```
Client → POST /api/workflows/:id/run → JWT Auth → Service Layer → Executor → Queue → Response (execution_id)
```

### Get Execution Logs
```
Client → GET /api/executions/:id/logs → JWT Auth → Repository → Database → Response (with logs)
```

---

## Implementation Status

### Phase -1 (Existing)
- ✅ Health checks
- ✅ Webhooks API
- ✅ Security headers
- ✅ Error handling

### Phase 0 (Completed)
- ✅ JWT authentication
- ✅ Workflows API (structure)
- ✅ Executions API (structure)
- ✅ MCP API (structure)
- ✅ Secrets API (structure)
- ✅ Pydantic schemas
- ✅ Consistent error format

### Next Phase (Pending)
- ⏳ Database implementation
- ⏳ Service layer implementation
- ⏳ Repository implementation
- ⏳ Actual execution logic
- ⏳ MCP integration
- ⏳ Secret store integration
- ⏳ Unit tests
- ⏳ Integration tests

---

## Testing Checklist

### Manual Testing (via Swagger UI)
1. Access http://localhost:8000/docs
2. Authorize with JWT token
3. Test each endpoint:
   - [ ] List workflows
   - [ ] Create workflow
   - [ ] Get workflow
   - [ ] Update workflow
   - [ ] Delete workflow
   - [ ] Run workflow
   - [ ] Validate workflow
   - [ ] List executions
   - [ ] Get execution
   - [ ] Stop execution
   - [ ] Resume execution
   - [ ] Get execution logs
   - [ ] List MCP servers
   - [ ] Connect MCP server
   - [ ] Disconnect MCP server
   - [ ] List server tools
   - [ ] Check server health
   - [ ] List secrets
   - [ ] Create secret
   - [ ] Update secret
   - [ ] Delete secret

### Automated Testing (TODO)
- [ ] Unit tests for each endpoint
- [ ] Integration tests with database
- [ ] Authentication tests
- [ ] Error handling tests
- [ ] Validation tests

---

## Performance Considerations

### Pagination
- All list endpoints support `limit` and `offset`
- Default limit: 100
- Maximum limit: 1000

### Filtering
- Executions: Filter by `workflow_id` and `status`
- Logs: Filter by `node_id`

### Caching Opportunities
- Workflow definitions (rarely change)
- MCP server tool lists (static)
- Secret metadata (values never cached)

---

## Security Features

### Authentication
- JWT with configurable expiration
- Bearer token in Authorization header
- Role-based access (user/admin)

### Secrets Management
- Values never returned in responses
- Encrypted at rest (TODO: implement)
- Audit logging (TODO: implement)

### Webhooks
- HMAC signature verification
- Timestamp-based replay protection
- IP allowlist support

### Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- HSTS in production

---

## API Versioning Strategy

### Current
- No version prefix (v1 implied)
- All endpoints at root level

### Future (v2+)
- Add `/api/v2/...` prefix
- Maintain `/api/...` as v1 for backwards compatibility
- Deprecation warnings in headers

---

## Rate Limiting (TODO)

Planned rate limits:
- Anonymous: 10 req/min (health checks only)
- Authenticated: 1000 req/min
- Admin: 10000 req/min
- Per workflow execution: 100 concurrent

---

## Monitoring Endpoints (Future)

Planned for Phase 2+:
- `/metrics` - Prometheus metrics
- `/api/stats` - API usage statistics
- `/api/audit` - Audit log query

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set JWT secret
export JWT_SECRET="your-secret-key-here"

# Run server
python -m uvicorn app.main:app --reload

# Test health check
curl http://localhost:8000/health/live

# View API docs
open http://localhost:8000/docs
```
